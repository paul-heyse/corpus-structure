"""Independent recursive reference positions and consumer-specific collection policies."""

from functools import cache
from typing import Any

import pytest
import yaml

from corpus_structure.semantic import SourceArtifact, SourceBundle, prepare_release
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
            "Statement": {"attributes": {"id": {"identifier": True}}},
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
            "TaggedEntry": {
                "attributes": {
                    "id": {"identifier": True, "range": "Tag"},
                    "text": {},
                }
            },
            "Root": {
                "attributes": {
                    "plain": {},
                    "statement": {"range": "Statement"},
                    "claims": {"multivalued": True, "annotations": {"cs:reference_role": "fact"}},
                    "entities": {"range": "Tag", "multivalued": True},
                    "children": {
                        "range": "Child",
                        "multivalued": True,
                        "inlined": True,
                        "inlined_as_list": True,
                    },
                    "entries": {"range": "Entry", "multivalued": True, "inlined": True},
                    "tagged_entries": {
                        "range": "TaggedEntry",
                        "multivalued": True,
                        "inlined": True,
                    },
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
    assert {r.target for r in references if r.kind == "fact"} == {"f1", "f2", "f3", "a", "b"}
    assert {r.target for r in references if r.kind == "class"} == {"e1", "e2", "e3"}
    rewritten = rewrite_references(
        release,
        "Root",
        raw,
        classes={"e1": "E1", "e3": "E3"},
        facts={"f2": "F2", "f3": "F3"},
        collision="equal",
    )
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


def test_callable_class_resolution_uses_declared_ranges_and_actual_nested_positions():
    seen = []

    def resolve(reference):
        seen.append(reference)
        assert reference.target == "same"
        return {"Tag": "tag:actual", "Statement": "statement:actual"}[reference.range]

    raw = {
        "plain": "same",
        "statement": "same",
        "entities": ("same", "same"),
        "children": ({"entity": "same", "claims": ("same",)},),
    }
    rewritten = rewrite_references(
        prepared(), "Root", raw, classes=resolve, facts={"same": "fact:actual"}
    )
    assert rewritten == {
        "plain": "same",
        "statement": "statement:actual",
        "entities": ("tag:actual", "tag:actual"),
        "children": ({"entity": "tag:actual", "claims": ("fact:actual",)},),
    }
    assert {(item.range, item.path) for item in seen} == {
        ("Statement", ("statement",)),
        ("Tag", ("entities", 0)),
        ("Tag", ("entities", 1)),
        ("Tag", ("children", 0, "entity")),
    }


def test_callable_class_resolution_preserves_keyed_collision_refusals():
    raw = {"tagged_entries": {"a": {"id": "a", "text": "same"}, "b": {"id": "b", "text": "same"}}}

    def resolve(reference):
        assert reference.range == "Tag"
        return "tag:merged"

    result = rewrite_references(prepared(), "Root", raw, classes=resolve, collision="equal")
    assert result == {"tagged_entries": {"tag:merged": {"id": "tag:merged", "text": "same"}}}
    with pytest.raises(ReferencePositionError, match="collides"):
        rewrite_references(prepared(), "Root", raw, classes=resolve, collision="reject")
    raw["tagged_entries"]["b"]["text"] = "different"
    with pytest.raises(ReferencePositionError, match="collides"):
        rewrite_references(prepared(), "Root", raw, classes=resolve, collision="equal")


def test_proposal_and_domain_property_reference_use_declared_nonentity_carrier():
    from pathlib import Path

    from corpus_structure.methods.llm.cascade import PlacementPolicy
    from corpus_structure.semantic.proposals import locate_proposal, proposal_inputs
    from corpus_structure.semantic.rich_knowledge import rich_property_value
    from semantic.proposals_support import batch, frame

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
        ),
    )
    raw = batch()
    raw["claims"][0]["predicate"] = "https://example.org/tag"
    raw["claims"][0]["object"] = {"kind": "tag_ref", "target": "known:tag"}
    result = locate_proposal(
        release,
        raw,
        frame(),
        known_classes={"known:tag": ("https://example.org/Tag",)},
        placement_policy=PlacementPolicy(),
    )
    assert result.clean
    person = next(d for d in release.definitions if d.name == "Person")
    prop = next(p for p in person.properties if p.name == "tag")
    assert (
        rich_property_value(
            release, person, prop, raw["claims"][0]["object"], {"known:tag": "admitted:tag"}
        )
        == "admitted:tag"
    )
