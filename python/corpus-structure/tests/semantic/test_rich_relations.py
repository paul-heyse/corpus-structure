"""Independent expected occurrence views, with no analytical transport oracle."""

from dataclasses import replace
from types import SimpleNamespace

import pytest

from corpus_structure.semantic.analytical_kernels import (
    ViewAlternative,
    ViewClaim,
    ViewEntity,
    ViewFacts,
    ViewIdentity,
    ViewSpec,
)
from corpus_structure.semantic.rich_relations import RichRelationKernel


def kernel(check_active=lambda: None, observe_inputs=None):
    return RichRelationKernel(
        property_ids=frozenset({"p:value", "p:label"}),
        check_active=check_active,
        observe_inputs=observe_inputs,
    )


def test_actual_views_preserve_null_statement_same_slot_and_explicit_alternatives():
    a = ViewClaim("a", "p:value", "subject:1", None, None)
    claims = (
        a,
        replace(a, claim="b"),
        replace(a, claim="c", statement="statement:other"),
        ViewClaim("label", "p:label", "subject:1", "entity:label", None),
        replace(a, claim="n", subject="subject:2"),
        a,  # Duplicate source rows never multiply facts or output rows.
    )
    entities = tuple(
        ViewEntity("entity:label", None, kind, "Observed", None)
        for kind in ("kind:actual", "kind:second", "kind:actual")
    )
    identity = (
        ViewIdentity("entity:label", "slot:one", "z"),
        ViewIdentity("entity:label", "slot:one", "a"),
        ViewIdentity("entity:label", "slot:one", "z"),
        ViewIdentity("entity:label", "slot:other", "excluded"),
    )
    alternatives = tuple(
        ViewAlternative("alternative:actual", claim) for claim in ("a", "c", "c", "absent")
    )
    specs = tuple(
        ViewSpec(
            name, frozenset({"p:value"}), "p:label", "subject", "subject", "object", attr, slot
        )
        for name, attr, slot in (
            ("labels", "label", None),
            ("classes", "types", None),
            ("identities", "identity", "slot:one"),
            ("keys", "key", None),
            ("ids", "id", None),
        )
    )
    observed = []
    output = kernel(observe_inputs=observed.append).views(
        claims=claims,
        entities=entities,
        identity=identity,
        alternatives=alternatives,
        specs=specs,
    )
    expected = []
    for claim in ("a", "b", "c", "label", "n"):
        expected.extend(
            (
                ViewFacts(claim, "same_slot", {"a": ("b",), "b": ("a",)}.get(claim, ())),
                ViewFacts(claim, "alternative_of", {"a": ("c",), "c": ("a",)}.get(claim, ())),
            )
        )
        if claim != "label":
            expected.extend(
                ViewFacts(claim, name, values if claim != "n" else ())
                for name, values in (
                    ("labels", ("Observed",)),
                    ("classes", ("kind:actual", "kind:second")),
                    ("identities", ("a", "z")),
                    ("keys", ()),
                    ("ids", ("entity:label",)),
                )
            )
    assert output == tuple(sorted(expected, key=lambda row: (row.claim, row.view)))
    assert observed == [dict(claims=6, entities=3, identity=4, alternatives=4, specs=5, applies=5)]


def test_absent_endpoints_never_join_and_subject_heads_project():
    claims = (
        ViewClaim("value", "p:value", "subject:1", None, None),
        ViewClaim("source", "p:label", "subject:1", None, None),
    )
    specs = (
        ViewSpec(
            "absent", frozenset({"p:value"}), "p:label", "object", "object", "subject", "label"
        ),
        ViewSpec(
            "subject", frozenset({"p:value"}), "p:label", "subject", "subject", "subject", "label"
        ),
        ViewSpec("no-target", frozenset(), "p:label", "subject", "subject", "subject", "label"),
    )
    rows = kernel().views(
        claims=claims,
        entities=(ViewEntity("subject:1", None, "class", "Present", None),),
        identity=(),
        alternatives=(),
        specs=specs,
    )
    assert {(row.claim, row.view): row.facts for row in rows} == {
        ("source", "alternative_of"): (),
        ("source", "same_slot"): (),
        ("value", "alternative_of"): (),
        ("value", "same_slot"): (),
        ("value", "absent"): (),
        ("value", "subject"): ("Present",),
    }


def test_declarations_keep_actual_release_property_authority():
    unowned = ViewSpec(
        "unowned", frozenset({"p:value"}), "p:forged", "subject", "subject", "object", "label"
    )
    with pytest.raises(ValueError, match="outside this release"):
        kernel().views(claims=(), entities=(), identity=(), alternatives=(), specs=(unowned,))
    owned = replace(unowned, source="p:label")
    with pytest.raises(ValueError, match="view names repeat"):
        kernel().views(claims=(), entities=(), identity=(), alternatives=(), specs=(owned, owned))


def test_cancellation_does_not_leave_an_invocation_resource_owner():
    calls = []

    def check():
        calls.append(None)
        if len(calls) == 2:
            raise InterruptedError("cancelled")

    scope = kernel(check)
    with pytest.raises(InterruptedError):
        scope.views(claims=(), entities=(), identity=(), alternatives=(), specs=())
    assert scope.views(claims=(), entities=(), identity=(), alternatives=(), specs=()) == ()


def test_model_entity_slot_rename_requires_a_matching_working_shape(monkeypatch):
    view = SimpleNamespace(
        get_class=lambda name: SimpleNamespace(
            attributes={name: None for name in ("id", "key", "types", "caption", "symbol")}
        )
    )
    monkeypatch.setattr(
        "corpus_structure.model.compiled.running_model",
        lambda: SimpleNamespace(view=lambda name: view),
    )
    with pytest.raises(ValueError, match="typed working shape: caption"):
        kernel().views(claims=(), entities=(), identity=(), alternatives=(), specs=())
