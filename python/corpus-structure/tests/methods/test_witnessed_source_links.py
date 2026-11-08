import json
from dataclasses import replace
from hashlib import sha256
from types import SimpleNamespace

import pytest

from corpus_structure.methods.scoped_relations import ScopedRelationsMethod, discover_relations
from corpus_structure.semantic.identity import canonical_bytes
from corpus_structure.semantic.observations import source_python, source_value
from corpus_structure.semantic.proposals import native_source_frame
from corpus_structure.semantic.source_contexts import record_source_pin
from corpus_structure.serve.witnessed_source_link_replay import verify_witnessed_links

from .test_inline_formula_occurrences import _FROZEN_TEXT
from .test_m1_source_preparation import source
from .test_scoped_relations import complete_native_fields

_DECLARATION = (
    "Let Z be a normal random variable with parameters µ = 0 and \u03c3 = 1. "
    "A normal random variable with these parameters is said to be a "
    "standard normal random variable. "
    "It is an important and useful fact that if we write"
)


def frozen(distraction="", *, different_parent=False, clipped=False):
    blocks = (
        (_DECLARATION, distraction, _FROZEN_TEXT)
        if distraction
        else (
            _DECLARATION,
            _FROZEN_TEXT,
        )
    )
    view = complete_native_fields(source("\n".join(blocks), labels=("text",) * len(blocks)))
    pieces = tuple(
        dict(p, source_field="text") if p["kind"] == "native_text" else p for p in view.pieces
    )
    items = tuple(
        dict(
            n,
            content_layer="body",
            parent={
                "$ref": "#/groups/2" if different_parent and i == len(blocks) - 1 else "#/groups/1",
            },
        )
        for i, n in enumerate(view.items)
    )
    projection = dict(
        text=view.text,
        pieces=pieces,
        items=[n["self_ref"] for n in items],
        ancestors=[],
        health={},
    )
    view = replace(
        view,
        pieces=pieces,
        items=items,
        ref=replace(view.ref, projection_digest=sha256(canonical_bytes(projection)).hexdigest()),
    )
    frame = native_source_frame(view, ())
    passage = SimpleNamespace(
        passage_id="standard-normal",
        start=1 if clipped else 0,
        end=len(view.text),
        scope="normal-variates",
        effective_version=None,
        source_ref="original",
    )
    report = discover_relations(
        frame,
        inline_equations_enabled=True,
        witnessed_links_enabled=True,
        passages=(passage,),
    )
    return frame, view, passage, report


def test_formula_uses_only_the_source_declared_symbol():
    frame, view, passage, output = frozen()
    rows = output["contributions"]
    (op,) = [op for op in output["extra_operations"] if op["question"] == "source_witnessed_links"]
    (relation,) = [
        r for r in rows if r["kind"] == "relation" and r["operation_key"] == op["operation_key"]
    ]
    by_id = {r["contribution_id"]: r for r in rows}
    use, target = [by_id[e["contribution_id"]] for e in relation["endpoints"]]
    assert (use["anchors"][0]["start"], use["anchors"][0]["end"]) == (242, 243)
    assert use["anchors"][0]["source_piece"] == "Z"
    assert (target["anchors"][0]["start"], target["anchors"][0]["end"]) == (130, 161)
    assert target["anchors"][0]["source_piece"] == "standard normal random variable"
    assert relation["component"]["attachment_kind"] == "declares"
    assert relation["component"]["scope"] == "normal-variates"
    assert source_python(use["value"])["syntax_standing"] == "syntax_only"

    body = json.loads(
        canonical_bytes(
            dict(
                operation_version=ScopedRelationsMethod.version,
                contribution_operations=(output["operation"], *output["extra_operations"]),
                contributions=rows,
                parse_detail=source_value({"formula_syntax": output["formula_diagnostics"]}),
            )
        )
    )
    original = {
        "source_view_id": frame.source_view_id,
        "text": frame.text,
        "context": {"items": view.items, "pieces": view.pieces},
    }
    inputs = SimpleNamespace(
        sources=(SimpleNamespace(identity="original", source_view_id=frame.source_view_id),),
        passages=(passage,),
    )
    verify_witnessed_links({"body": body}, original, record_source_pin(frame), inputs)
    forged = next(
        r for r in body["contributions"] if r["contribution_id"] == relation["contribution_id"]
    )
    forged["computation_dependencies"].remove(
        next(
            r["contribution_id"]
            for r in rows
            if r["operation_key"] == op["operation_key"]
            and r["kind"] == "occurrence"
            and source_python(r["value"])["role"] == "declaration_recap"
        )
    )
    with pytest.raises(ValueError, match="declared direction or premises"):
        verify_witnessed_links({"body": body}, original, record_source_pin(frame), inputs)


@pytest.mark.parametrize(
    "kwargs",
    [
        {"distraction": "Let Z be a different variable."},
        {"different_parent": True},
        {"clipped": True},
    ],
)
def test_formula_ambiguity_or_partial_scope_keeps_the_syntax(kwargs):
    _, _, _, output = frozen(**kwargs)
    assert any(o["question"] == "source_formula_occurrences" for o in output["extra_operations"])
    assert not any(o["question"] == "source_witnessed_links" for o in output["extra_operations"])


def test_named_links_use_literal_anchors_and_never_choose_first_section():
    from corpus_structure.methods.witnessed_source_links import named_source_links

    lines = (
        "Central Limit Theorem (CLT).",
        "Old Control is hereafter called New Control.",
        "Version B supersedes Version A.",
        "See Section 6.1.",
        "6.1 First candidate",
        "6.1 Second candidate",
        "The law is as defined in Section 6.2.",
        "6.2 One explicit target",
        "See Section 9.9.",
        "See Box and Muller.9",
    )
    labels = (
        "text",
        "text",
        "text",
        "text",
        "section_header",
        "section_header",
        "text",
        "section_header",
        "text",
        "text",
    )
    view = source("\n".join(lines), labels=labels)
    items = {i["self_ref"]: dict(i, content_layer="body") for i in view.items}
    passage = SimpleNamespace(start=0, end=len(view.text), scope="work", passage_id="chapter")
    links = tuple(named_source_links(view.text, view.pieces, items, (passage,)))

    def literal(extent):
        return view.text[slice(*extent)] if extent is not None else None

    assert [(x.kind, literal(x.left), literal(x.right)) for x in links] == [
        ("alias", "Central Limit Theorem", "CLT"),
        ("alias", "Old Control", "New Control"),
        ("supersedes", "Version B", "Version A"),
        ("section_citation", "Section 6.1", None),
        ("definition_reference", "Section 6.2", "6.2 One explicit target"),
        ("section_citation", "Section 9.9", None),
        ("external_citation", "Box and Muller.9", None),
    ]
    assert links[-1].resolution == "external_target_unavailable"


def test_retained_named_link_recipe_preserves_roles_and_refuses_inferred_endpoints():
    from corpus_structure.methods.source_preparation import prepare_source
    from corpus_structure.methods.witnessed_source_links import match_named_source_links
    from corpus_structure.semantic.structural_products import StructuralPassage

    lines = (
        "For comparison, see Section 5.2.",
        "The scope is as defined in Section 6.3.",
        "Central Limit Theorem (CLT).",
        "Conditional Limit Theory, hereafter CLT, applies only in this experiment.",
        "Old Control is hereafter called New Control.",
        "Old Control was renamed to New Control.",
        "Version B supersedes Version A.",
        "Version A is superseded by Version C.",
        "New Control specializes Old Control.",
        "New Control does not specialize Standard Control.",
        'The note says "Version D supersedes Version C".',
        "Use Table 6.1 for this procedure.",
        "See Box and Muller.9",
    )
    view = complete_native_fields(source("\n".join(lines), labels=("text",) * len(lines)))
    view = replace(view, items=tuple(dict(item, content_layer="body") for item in view.items))
    prepared = prepare_source(view, annotations_only=True)
    assert not prepared.annotation_errors
    passage = StructuralPassage(
        passage_id="chapter",
        source_ref="fixture",
        start=0,
        end=len(view.text),
        scope="fixture-work",
        effective_version="R2",
        text=view.text,
    )
    result = match_named_source_links(
        view.text,
        view.pieces,
        {item["self_ref"]: item for item in view.items},
        (passage,),
        prepared.annotations,
    )

    def literal(extent):
        return view.text[slice(*extent)] if extent is not None else None

    by_kind = {
        (match.kind, literal(match.left), literal(match.right)): match for match in result.matches
    }
    assert result.inspected_count == len(lines)
    assert result.outcome() == "limited"
    for kind, subject, argument, resolution in (
        ("section_citation", "Section 5.2", None, "target_selection_required"),
        ("definition_reference", "Section 6.3", None, "target_selection_required"),
        ("alias", "Central Limit Theorem", "CLT", "located"),
        ("alias", "Conditional Limit Theory", "CLT", "located"),
        ("alias", "Old Control", "New Control", "located"),
        ("renames", "Old Control", "New Control", "located"),
        ("supersedes", "Version B", "Version A", "located"),
        ("supersedes", "Version C", "Version A", "located"),
        ("specializes", "New Control", "Old Control", "located"),
        ("specializes", "New Control", "Standard Control", "insufficient_evidence"),
        ("supersedes", "Version D", "Version C", "insufficient_evidence"),
        ("procedure_reference", "Table 6.1", "Use", "target_selection_required"),
        ("external_citation", "Box and Muller.9", None, "external_target_unavailable"),
    ):
        key = (kind, subject, argument)
        assert key in by_kind, sorted(by_kind)
        match = by_kind[key]
        assert match.resolution == resolution
        assert (match.witness.scope, match.witness.effective_version) == ("fixture-work", "R2")
        assert match.witness.tokens and match.witness.annotation.startswith("annotation:")
        assert (match.target_pointer is not None) == (resolution == "located")
