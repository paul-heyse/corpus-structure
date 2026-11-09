import json
from dataclasses import replace
from hashlib import sha256
from types import SimpleNamespace

import pytest

from corpus_structure.methods.scoped_relations import (
    ScopedRelationsConfig,
    ScopedRelationsMethod,
    ScopedRelationsOrderedConfig,
    discover_relations,
)
from corpus_structure.semantic.identity import canonical_bytes
from corpus_structure.semantic.observations import source_python, source_value
from corpus_structure.semantic.proposals import native_source_frame
from corpus_structure.semantic.source_contexts import record_source_pin
from corpus_structure.semantic.structural_products import (
    ExternalSourceRef,
    StructuralInput,
    StructuralPassage,
)
from corpus_structure.serve.inline_formula_replay import verify_inline_formula_report
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


def ordered_fixture(*, control=None):
    first = (
        "Let V be a calibration signal with parameters A = 0 and B = 1. A\n"
        "calibration signal with these parameters is said to be a "
    )
    middle, last = "standard", " calibration\nsignal."
    recap = (
        "We have seen above that it is possible to simulate a standard calibration signal V. "
        "We use the simulated values for V using the equation "
        + ("O = V + V." if control == "repeated-use" else "O = B V + A.")
    )
    section, wrapper, inline = "#/groups/1", "#/texts/0", "#/groups/2"
    first_ref, middle_ref, last_ref, recap_ref, rival_ref = (f"#/texts/{i}" for i in range(1, 6))
    second_ref = "#/texts/6"

    def ref(pointer):
        return {"$ref": pointer}

    def node(pointer, label, text="", *, parent=None, children=()):
        return dict(
            self_ref=pointer,
            label=label,
            text=text,
            content_layer="body",
            parent=ref(parent) if parent else None,
            children=tuple(map(ref, children)),
        )

    child_refs = (first_ref, middle_ref, last_ref)
    declaration = first + middle + last
    rival = "Suppose V denotes another signal.\n" if control == "rival" else ""
    second = control == "two-recaps"
    siblings = (wrapper, *((rival_ref,) if rival else ()), recap_ref)
    if second:
        siblings += (second_ref,)
    context_nodes = (
        node(section, "section", children=siblings),
        node(wrapper, "text", parent=section, children=(inline,)),
        node(
            inline,
            "inline",
            parent=wrapper,
            children=child_refs[::-1] if control == "order" else child_refs,
        ),
        node(first_ref, "text", first, parent=inline),
        node(middle_ref, "text", middle, parent=inline),
        node(last_ref, "text", last, parent=inline),
        node(recap_ref, "text", recap, parent=inline if control == "foreign" else section),
        *((node(rival_ref, "text", rival[:-1], parent=section),) if rival else ()),
        *((node(second_ref, "text", recap, parent=section),) if second else ()),
    )
    chunks = [(first_ref, first), (middle_ref, middle), (last_ref, last), (None, "\n")]
    if rival:
        chunks.extend(((rival_ref, rival[:-1]), (None, "\n")))
    chunks.append((recap_ref, recap))
    query_text = recap
    if second:
        chunks.extend(((None, "\n"), (second_ref, recap)))
        query_text += "\n" + recap
    offset, pieces = 0, []
    for pointer, literal in chunks:
        end = offset + len(literal)
        if pointer is None or (pointer == middle_ref and control == "synthetic"):
            pieces.append(dict(start=offset, end=end, kind="synthetic_separator"))
        else:
            pieces.append(
                dict(
                    start=offset, end=end, item_ref=pointer, kind="native_text", source_field="text"
                )
            )
        offset = end
    text = declaration + "\n" + rival + query_text
    original = source("placeholder", labels=("text",))
    projection = dict(
        text=text,
        pieces=pieces,
        items=[n["self_ref"] for n in context_nodes],
        ancestors=[],
        health={},
    )
    view = replace(
        original,
        text=text,
        items=context_nodes,
        pieces=tuple(pieces),
        ref=replace(
            original.ref, projection_digest=sha256(canonical_bytes(projection)).hexdigest()
        ),
    )
    scope = dict(source_ref="original", scope="instrument-calibration", effective_version="R2")
    query = StructuralPassage(
        passage_id="original-query",
        start=len(text) - len(query_text),
        end=len(text),
        text=query_text,
        **scope,
    )
    wider = StructuralPassage(
        passage_id="wider-premises", start=0, end=len(text), text=text, **scope
    )
    return view, query, wider


def ordered_run(view, query, wider):
    frame = native_source_frame(view, ())
    external = ExternalSourceRef(
        project_id="fixture",
        run_id=1,
        cut_id=1,
        release_id="fixture",
        result_revision=0,
        source_view_id=frame.source_view_id,
        native_task_id=frame.native_product.task_id,
        native_product_key=frame.native_product.product_key,
        native_content_digest=frame.native_product.content_digest,
        projection_digest=frame.projection_digest,
        recipe_digest=frame.recipe_digest,
        coordinate_version=3,
    )
    query = query.model_copy(update={"source_ref": external.identity})
    wider = wider.model_copy(update={"source_ref": external.identity})
    inputs = StructuralInput(
        question="formula witness",
        scope=query.scope,
        inventory_id="inventory",
        policy_id="fixture",
        sources=(external,),
        passages=(query,),
        dependencies=("fixture",),
    )
    config = ScopedRelationsOrderedConfig(
        inputs=inputs, structural_input_digest=inputs.identity, ordered_formula_witness=wider
    )
    output = discover_relations(
        frame,
        inline_equations_enabled=True,
        witnessed_links_enabled=True,
        passages=(query,),
        predicate_version="5",
        ordered_formula_witness=wider,
    )
    operations = (output["operation"], *output["extra_operations"])
    (witness,) = [o for o in operations if o["question"] == "source_witnessed_links"]
    report = json.loads(
        canonical_bytes(
            dict(
                configuration=config.model_dump(mode="json"),
                body=dict(
                    operation_version="11",
                    contribution_operations=operations,
                    contributions=output["contributions"],
                    parse_detail=source_value({"formula_syntax": output["formula_diagnostics"]}),
                ),
            )
        )
    )
    source = {
        "source_view_id": frame.source_view_id,
        "text": frame.text,
        "ref": {
            "key": frame.unit_ref,
            "projection_digest": frame.projection_digest,
            "recipe_digest": frame.recipe_digest,
            "native_product": {
                "task_id": frame.native_product.task_id,
                "product_key": frame.native_product.product_key,
                "content_digest": frame.native_product.content_digest,
            },
        },
        "context": {"items": view.items, "ancestors": view.ancestors, "pieces": view.pieces},
    }
    verify_inline_formula_report(report, source)
    return witness, report, source


def test_ordered_formula_witness_keeps_exact_pieces_and_original_formula_population():
    view, query, wider = ordered_fixture()
    op, report, source = ordered_run(view, query, wider)
    rows = report["body"]["contributions"]
    by_id = {r["contribution_id"]: r for r in rows}
    (link,) = [
        r for r in rows if r["operation_key"] == op["operation_key"] and r["kind"] == "relation"
    ]
    use, name = map(by_id.__getitem__, link["members"])
    assert (op["operation_version"], op["outcome"], op["inspected_count"], op["emitted_count"]) == (
        "2",
        "succeeded",
        1,
        3,
    )
    assert source_python(use["value"])["text"] == "V"
    assert {"O", "V"} <= {
        source_python(r["value"])["text"]
        for r in rows
        if r["kind"] == "occurrence" and source_python(r["value"])["role"] == "formula_symbol"
    }
    assert source_python(name["value"])["text"] == "standard calibration\nsignal"
    assert [(a["pointer"], a["start"], a["end"], a["source_piece"]) for a in name["anchors"]] == [
        ("#/texts/2", 0, 8, "standard"),
        ("#/texts/3", 0, 19, " calibration\nsignal"),
    ]
    assert link["component"]["effective_version"] == "R2"
    assert source_python(name["value"])["source_pointer"] == "#/texts/2"
    assert source_python(name["value"])["region"] == wider.passage_id

    name["anchors"].reverse()
    with pytest.raises(ValueError, match="exact named target"):
        verify_inline_formula_report(report, source)
    name["anchors"].reverse()
    report["body"]["contributions"] = [r for r in rows if r["operation_key"] != op["operation_key"]]
    (claimed,) = [
        o
        for o in report["body"]["contribution_operations"]
        if o["operation_key"] == op["operation_key"]
    ]
    claimed.update(outcome="limited", emitted_count=0)
    with pytest.raises(ValueError, match="exact named target"):
        verify_inline_formula_report(report, source)
    prior = link["computation_dependencies"][-1]
    report["body"]["contributions"] = [
        r for r in report["body"]["contributions"] if r["contribution_id"] != prior
    ]
    with pytest.raises(ValueError, match="one exact prior binding"):
        verify_inline_formula_report(report, source)


def test_ordered_formula_witness_refuses_same_extent_or_changed_source_bytes():
    view, query, wider = ordered_fixture()
    with pytest.raises(ValueError, match="bounded selected source"):
        ordered_run(view, query, wider.model_copy(update={"text": "!" + wider.text[1:]}))
    with pytest.raises(ValueError, match="same exact query scope"):
        ordered_run(view, query, query.model_copy(update={"passage_id": "relabelled"}))

    original, *_ = ordered_run(view, query, wider)
    clipped, *_ = ordered_run(
        view, query.model_copy(update={"start": query.start + 1, "text": query.text[1:]}), wider
    )
    assert clipped["outcome"] == "empty"
    assert clipped["operation_key"] != original["operation_key"]


@pytest.mark.parametrize(
    ("control", "outcome", "count"),
    [
        ("rival", "limited", 1),
        ("order", "limited", 1),
        ("synthetic", "limited", 1),
        ("foreign", "empty", 0),
        ("repeated-use", "limited", 1),
    ],
)
def test_ordered_formula_witness_refuses_incomplete_or_ambiguous_source(control, outcome, count):
    op, report, *_ = ordered_run(*ordered_fixture(control=control))
    assert (op["outcome"], op["inspected_count"], op["emitted_count"]) == (outcome, count, 0)
    assert any(
        operation["question"] == "source_formula_occurrences"
        and operation["outcome"] == "succeeded"
        for operation in report["body"]["contribution_operations"]
    )


def test_ordered_formula_witness_uses_one_physical_target_for_two_inspected_recaps():
    op, report, _ = ordered_run(*ordered_fixture(control="two-recaps"))
    assert (op["outcome"], op["inspected_count"], op["emitted_count"]) == ("succeeded", 2, 5)
    links = [
        row
        for row in report["body"]["contributions"]
        if row["operation_key"] == op["operation_key"] and row["kind"] == "relation"
    ]
    assert len({row["members"][0] for row in links}) == 2
    assert len({row["members"][1] for row in links}) == 1


def test_ordered_witness_is_a_new_opt_in_method_contract(tmp_path):
    from corpus_structure.orchestrate.phase0 import registry

    method_name = "structure.scoped_relations"
    default = registry(tmp_path).method(method_name)
    assert default.version == "10"
    assert default.Config is ScopedRelationsConfig
    assert "ordered_formula_witness" not in default.Config.model_fields
    _, report, _ = ordered_run(*ordered_fixture())
    (tmp_path / "methods.yaml").write_text(
        json.dumps({"configs": {method_name: {"witness": report["configuration"]}}})
    )
    selected = registry(tmp_path)
    method = selected.method(method_name)
    assert method.version == "11"
    assert method.Config is ScopedRelationsOrderedConfig
    cfg = selected.overlay(method_name, "witness")
    run = SimpleNamespace(
        reader=SimpleNamespace(
            source_views=lambda: (
                SimpleNamespace(id=7, key="source:7"),
                SimpleNamespace(id=8, key="source:8"),
            )
        )
    )
    (source,) = method.select(run, cfg)
    assert source.unit_id == 7


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
