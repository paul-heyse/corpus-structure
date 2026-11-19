"""Independent rich identity cases over selected semantic source products."""

from copy import deepcopy
from functools import lru_cache
from pathlib import Path
from typing import Any

import pytest
import yaml

from corpus_structure.semantic.data_operation_model import SubjectContext
from corpus_structure.semantic.prepare import prepare_release
from corpus_structure.semantic.rich_knowledge import (
    RichEntitySource,
    RichIdentityConflict,
    RichKnownEntity,
    RichKnownEntityIdentity,
    resolve_rich_entities,
)
from corpus_structure.semantic.types import SourceArtifact, SourceBundle
from semantic.identity_resolution_support import source_values


@lru_cache(maxsize=4)
def release(keyed=False, local=False):
    core = Path(__file__).parents[2] / "src/corpus_structure/model/semantic/core.yaml"
    classes: dict[str, dict[str, Any]] = {}
    for name, primitive in (("Person", "string"), ("Device", "integer")):
        classes[name] = {
            "is_a": "Entity",
            "annotations": {"cs:scope": "local" if local else "global"},
            "attributes": {"serial": {"range": primitive}},
        }
        if keyed:
            classes[name]["unique_keys"] = {"serial": {"unique_key_slots": ["serial"]}}
    domain = {
        "id": "https://example.org/identity",
        "name": "identity",
        "imports": ["core"],
        "prefixes": {"ex": "https://example.org/"},
        "default_prefix": "ex",
        "classes": classes,
    }
    return prepare_release(
        SourceBundle(
            "domain",
            (
                SourceArtifact("core", core.read_bytes()),
                SourceArtifact("domain", yaml.safe_dump(domain).encode()),
            ),
        )
    )


def source_context(*, project="project:one", document="original:one"):
    return SubjectContext(
        project, "source:one", document, b"null", subject_definition="original-source-view"
    )


def selected(
    *,
    keyed=False,
    located=True,
    project="project:one",
    document="original:one",
    reference='["product:proposals",null]',
):
    # Only source-authored semantic entity/exclusion values are reused here. There
    # is no run/task/observation or historical batch in the current kernel input.
    values = source_values(keyed=keyed, located=located)
    return RichEntitySource(
        reference,
        source_context(project=project, document=document),
        tuple(values["entities"]),
        tuple(values["identity_exclusions"]),
        {},
    )


def resolve(
    sources,
    *,
    keyed=False,
    local=False,
    known=None,
    kind="kind:person",
    universe="knowledge:one",
    project="project:one",
):
    return resolve_rich_entities(
        release(keyed, local),
        entity_contracts={
            "https://example.org/Person": kind,
            "https://example.org/Device": "kind:device",
        },
        universe=SubjectContext(
            project, universe, None, b"null", subject_definition="knowledge-universe"
        ),
        sources=sources,
        known=known or {},
    )


def test_current_cannot_link_and_required_keys_keep_independent_semantics():
    mapping, decisions = resolve((selected(),))
    values = mapping[selected().reference]
    assert values["a"] == values["b"] and values["a"] != values["c"]
    assert all(row.basis == "global_label" and row.outcome == "resolved" for row in decisions)
    with pytest.raises(RichIdentityConflict) as error:
        resolve((selected(keyed=True),), keyed=True)
    assert error.value.exclusion_id == "split"
    assert error.value.left == {"kind": "local", "target": "a"}
    assert error.value.right == {"kind": "local", "target": "c"}
    assert len(set(resolve((selected(located=False),))[0][selected().reference].values())) == 1


def test_known_anchors_and_ambiguous_labels_do_not_choose_by_order():
    original = selected()
    entities = RichKnownEntity(
        (RichKnownEntityIdentity("https://example.org/Person", {}, None, "Alice"),)
    )
    known = {"known:one": entities, "known:two": entities}
    left, decisions = resolve((original,), known=known)
    right, _ = resolve((original,), known=dict(reversed(tuple(known.items()))))
    assert left == right and not set(left[original.reference].values()) & known.keys()
    assert all(row.outcome == "ambiguous_anchor" for row in decisions)
    assert all(row.matched_entity_ids == ("known:one", "known:two") for row in decisions)
    assert all(row.candidate_identity_keys == () for row in decisions)
    changed = deepcopy(original.exclusions[0])
    changed["right"] = {"kind": "known", "target": "known:one"}
    constrained = RichEntitySource(
        original.reference, original.context, original.entities, (changed,), {}
    )
    mapping, _ = resolve((constrained,), known={"known:one": entities})
    assert mapping[original.reference]["a"] != "known:one"


def test_known_multiple_class_keys_keep_their_actual_property_namespaces():
    known = {
        "known:hybrid": RichKnownEntity(
            (
                RichKnownEntityIdentity("https://example.org/Person", {"serial": "same"}, None),
                RichKnownEntityIdentity("https://example.org/Device", {"serial": 7}, None),
            )
        )
    }
    proposals = RichEntitySource(
        '["product:class-scoped",null]',
        source_context(),
        (
            {
                "id": "person",
                "class_iri": "https://example.org/Person",
                "attributes": [
                    {
                        "predicate": "https://example.org/serial",
                        "value": {"kind": "text", "text": "same"},
                    },
                ],
            },
            {
                "id": "device",
                "class_iri": "https://example.org/Device",
                "attributes": [
                    {
                        "predicate": "https://example.org/serial",
                        "value": {"kind": "number", "number": 7},
                    },
                ],
            },
        ),
        (),
        {},
    )
    mapping, decisions = resolve((proposals,), keyed=True, known=known)
    assert mapping[proposals.reference] == {"person": "known:hybrid", "device": "known:hybrid"}
    assert all(row.matched_entity_ids == ("known:hybrid",) for row in decisions)
    assert len({row.candidate_identity_keys for row in decisions}) == 2


def test_known_labels_remain_scoped_to_their_actual_class():
    known = {
        "known:person": RichKnownEntity(
            (
                RichKnownEntityIdentity("https://example.org/Person", {}, None, "Alice"),
                RichKnownEntityIdentity("https://example.org/Device", {}, None, "Meter"),
            )
        ),
        "known:device": RichKnownEntity(
            (
                RichKnownEntityIdentity("https://example.org/Person", {}, None, "Bob"),
                RichKnownEntityIdentity("https://example.org/Device", {}, None, "Alice"),
            )
        ),
    }
    original = selected()
    proposals = RichEntitySource(original.reference, original.context, original.entities, (), {})
    mapping, decisions = resolve((proposals,), known=known)
    assert set(mapping[proposals.reference].values()) == {"known:person"}
    assert all(row.matched_entity_ids == ("known:person",) for row in decisions)


def test_unmatched_declared_keys_are_not_reported_as_matched_entities():
    original = selected(keyed=True)
    proposals = RichEntitySource(
        original.reference, original.context, original.entities[:1], (), {}
    )
    mapping, (decision,) = resolve((proposals,), keyed=True)
    assert decision.entity_id == mapping[proposals.reference]["a"]
    assert len(decision.candidate_identity_keys) == 1
    assert decision.matched_entity_ids == ()


@pytest.mark.parametrize("local", [False, True])
def test_declared_local_keys_preserve_actual_source_context_without_rewriting_values(local):
    first = selected(keyed=True, reference='["product:one",null]')
    other = selected(keyed=True, reference='["product:two",null]', document="original:two")
    one = RichEntitySource(first.reference, first.context, first.entities[:1], (), {})
    two = RichEntitySource(other.reference, other.context, other.entities[:1], (), {})
    mapping, _ = resolve((one, two), keyed=True, local=local)
    assert (mapping[one.reference]["a"] != mapping[two.reference]["a"]) is local
    # A new reading of the same actual source can reuse its declared key basis.
    known = {
        "known:one": RichKnownEntity(
            (
                RichKnownEntityIdentity(
                    "https://example.org/Person",
                    {"serial": "same"},
                    one.context if local else None,
                ),
            )
        )
    }
    another_reading = RichEntitySource(
        '["product:another-reading",null]', one.context, one.entities, (), {}
    )
    mapping, decisions = resolve((one, two, another_reading), keyed=True, local=local, known=known)
    assert mapping[one.reference]["a"] == "known:one"
    assert mapping[another_reading.reference]["a"] == "known:one"
    assert (mapping[two.reference]["a"] != "known:one") is local
    assert next(
        row for row in decisions if row.source_reference == one.reference
    ).matched_entity_ids == ("known:one",)
    assert one.entities[0]["attributes"][0]["value"] == {"kind": "text", "text": "same"}


def test_unscoped_authored_local_identity_does_not_become_a_global_key_anchor():
    first = selected(keyed=True)
    proposal = RichEntitySource(first.reference, first.context, first.entities[:1], (), {})
    known = {
        "authored:explicit": RichKnownEntity(
            (
                RichKnownEntityIdentity(
                    "https://example.org/Person",
                    {"serial": "same"},
                    None,
                ),
            )
        )
    }
    mapping, (decision,) = resolve((proposal,), keyed=True, local=True, known=known)
    assert mapping[proposal.reference]["a"] != "authored:explicit"
    assert decision.matched_entity_ids == ()


def test_current_identity_is_stable_by_source_address_not_order_or_broad_release():
    first = selected()
    second = selected(reference='["product:other",null]')
    left, _ = resolve((first, second))
    right, _ = resolve((second, first))
    assert left == right
    # Semantic kind/knowledge universe are consequential determinants.
    assert resolve((first,), kind="kind:changed")[0] != resolve((first,))[0]
    assert resolve((first,), universe="knowledge:other")[0] != resolve((first,))[0]
    assert (
        resolve((selected(project="project:other"),), project="project:other")[0]
        != resolve((first,))[0]
    )
    with pytest.raises(ValueError, match="knowledge project"):
        resolve((first,), project="project:other")
    with pytest.raises(ValueError, match="unique selected"):
        resolve((first, first))


def test_rich_source_refuses_legacy_and_unqualified_addresses():
    for reference in (
        "run:old",
        '"observation:one"',
        '["",null]',
        '["product:one"]',
        '["product:one",""]',
    ):
        with pytest.raises(ValueError):
            selected(reference=reference)


def test_current_scientific_context_needs_exact_archive_but_no_legacy_execution_binding():
    from dataclasses import replace

    from corpus_structure.semantic.identity import canonical_bytes
    from corpus_structure.semantic.math_context import acquire_analysis_context_profile
    from corpus_structure.semantic.scientific_evidence import (
        SCIENTIFIC_POLICY_INPUT,
        SemanticComparator,
        scientific_policy_recipe,
    )
    from corpus_structure.semantic.types import PreparedArtifact

    profile = acquire_analysis_context_profile()
    # Current comparison consumes the supplied semantic schema and explicit
    # captured policy, without acquiring an execution catalog.
    prepared = release()
    artifact = PreparedArtifact(
        SCIENTIFIC_POLICY_INPUT, canonical_bytes(scientific_policy_recipe(context_profile=profile))
    )
    prepared = replace(
        prepared,
        artifacts=(
            *(item for item in prepared.artifacts if item.kind != SCIENTIFIC_POLICY_INPUT),
            artifact,
        ),
    )
    comparator = SemanticComparator({}, prepared=prepared, context_profile=profile)
    equal = comparator.compare({"kind": "number", "number": 7}, {"kind": "number", "number": 7})
    different = comparator.compare({"kind": "number", "number": 7}, {"kind": "number", "number": 8})
    assert equal.equal is True and different.equal is False
    uncertain = comparator.compare(
        {
            "kind": "formula",
            "language": "latex",
            "expression": "x",
            "bindings": [{"kind": "unresolved", "symbol": "x"}],
        },
        {
            "kind": "formula",
            "language": "latex",
            "expression": "x+0",
            "bindings": [{"kind": "unresolved", "symbol": "x"}],
        },
    )
    assert uncertain.evidence.agreement is None and uncertain.tier == "undecided"
    changed = replace(
        prepared,
        artifacts=tuple(
            item for item in prepared.artifacts if item.kind != SCIENTIFIC_POLICY_INPUT
        ),
    )
    with pytest.raises(ValueError, match="recipe is unsupported"):
        SemanticComparator({}, prepared=changed, context_profile=profile)
