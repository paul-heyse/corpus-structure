"""Independent rich identity cases over selected semantic source products."""

from copy import deepcopy

import pytest

from corpus_structure.semantic.data_operation_model import SubjectContext
from corpus_structure.semantic.rich_knowledge import (
    RichEntitySource, RichKnownEntity, RichIdentityConflict, resolve_rich_entities,
)
from semantic.identity_resolution_support import release, source


def selected(*, keyed=False, located=True, reference='["product:proposals",null]'):
    # Only source-authored semantic entity/exclusion values are reused here. There
    # is no run/task/observation or historical batch in the current kernel input.
    values = source(keyed=keyed, located=located)["payload"]
    return RichEntitySource(reference, tuple(values["entities"]), tuple(values["identity_exclusions"]), {})


def resolve(sources, *, keyed=False, known=None, kind="kind:person", universe="knowledge:one", project="project:one"):
    return resolve_rich_entities(release(keyed), entity_contracts={"https://example.org/Person": kind}, universe=SubjectContext(project, universe, None, b"null", subject_definition="knowledge-universe"), sources=sources, known=known or {})


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
    entities = RichKnownEntity(("https://example.org/Person",), {}, "Alice")
    known = {"known:one": entities, "known:two": entities}
    left, decisions = resolve((original,), known=known)
    right, _ = resolve((original,), known=dict(reversed(tuple(known.items()))))
    assert left == right and not set(left[original.reference].values()) & known.keys()
    assert all(row.outcome == "ambiguous_anchor" for row in decisions)
    changed = deepcopy(original.exclusions[0])
    changed["right"] = {"kind": "known", "target": "known:one"}
    constrained = RichEntitySource(original.reference, original.entities, (changed,), {})
    mapping, _ = resolve((constrained,), known={"known:one": entities})
    assert mapping[original.reference]["a"] != "known:one"


def test_current_identity_is_stable_by_source_address_not_order_or_broad_release():
    first = selected()
    second = selected(reference='["product:other",null]')
    left, _ = resolve((first, second))
    right, _ = resolve((second, first))
    assert left == right
    # Semantic kind/knowledge universe are consequential determinants.
    assert resolve((first,), kind="kind:changed")[0] != resolve((first,))[0]
    assert resolve((first,), universe="knowledge:other")[0] != resolve((first,))[0]
    assert resolve((first,), project="project:other")[0] != resolve((first,))[0]
    with pytest.raises(ValueError, match="unique selected"):
        resolve((first, first))


def test_rich_source_refuses_legacy_and_unqualified_addresses():
    for reference in ("run:old", '"observation:one"', '["",null]', '["product:one"]', '["product:one",""]'):
        with pytest.raises(ValueError):
            selected(reference=reference)


def test_current_scientific_context_needs_exact_archive_but_no_legacy_execution_binding():
    from dataclasses import replace
    from corpus_structure.semantic.analysis_contracts import acquire_analysis_context_profile
    from corpus_structure.semantic.scientific_evidence import SCIENTIFIC_POLICY_INPUT, SemanticComparator, scientific_policy_recipe
    from corpus_structure.semantic.types import PreparedArtifact
    from corpus_structure.semantic.identity import canonical_bytes

    profile = acquire_analysis_context_profile()
    # Keep the genuine semantic schema and runtime manifest, remove its historical
    # operational model. The explicitly captured profile owns current comparison.
    prepared = replace(release(), execution_model_id=None)
    artifact = PreparedArtifact(SCIENTIFIC_POLICY_INPUT, canonical_bytes(scientific_policy_recipe(context_profile=profile)))
    prepared = replace(prepared, artifacts=tuple(item for item in prepared.artifacts if item.kind != SCIENTIFIC_POLICY_INPUT) + (artifact,))
    comparator = SemanticComparator({}, prepared=prepared, context_profile=profile)
    equal = comparator.compare({"kind": "number", "number": 7}, {"kind": "number", "number": 7})
    different = comparator.compare({"kind": "number", "number": 7}, {"kind": "number", "number": 8})
    assert equal.equal is True and different.equal is False
    uncertain = comparator.compare(
        {"kind": "formula", "language": "latex", "expression": "x", "bindings": [{"kind": "unresolved", "symbol": "x"}]},
        {"kind": "formula", "language": "latex", "expression": "x+0", "bindings": [{"kind": "unresolved", "symbol": "x"}]},
    )
    assert uncertain.evidence.agreement is None and uncertain.tier == "undecided"
    changed = replace(prepared, artifacts=tuple(item for item in prepared.artifacts if item.kind != SCIENTIFIC_POLICY_INPUT))
    with pytest.raises(ValueError, match="recipe is unsupported"):
        SemanticComparator({}, prepared=changed, context_profile=profile)
