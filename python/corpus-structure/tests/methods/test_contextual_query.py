"""Primary-node identity, exact native positions and bounded retrieval signals."""

from dataclasses import replace

import pytest

from corpus_structure.methods.contextual_embeddings import (
    E5,
    ContextCoreLimited,
    ContextInput,
    render_context,
)
from corpus_structure.methods.contextual_query import QueryContextSelection, resolve_query_contexts
from corpus_structure.semantic.characterization import LayerReport
from corpus_structure.semantic.contributions import occurrence_identity
from corpus_structure.semantic.identity import canonical_bytes
from methods.contextual_query_support import (
    POINTER as POINTER,
)
from methods.contextual_query_support import (
    TEXT as TEXT,
)
from methods.contextual_query_support import (
    anchor as anchor,
)
from methods.contextual_query_support import (
    frame_layer as frame_layer,
)
from methods.contextual_query_support import (
    primary as primary,
)
from methods.contextual_query_support import (
    source as source,
)


def resolve(recipe, layers, reference, focal, *, frame=None, pointer=POINTER):
    frame = frame or source()
    focal_anchor = anchor(focal, frame=frame, pointer=pointer)
    occurrence = occurrence_identity((focal_anchor,))
    selection = QueryContextSelection.model_validate(
        dict(
            recipe=recipe,
            bindings=[dict(occurrence_id=occurrence, evidence=reference.values())],
        )
    )
    return resolve_query_contexts(
        selection, layers, [dict(occurrence_id=occurrence, anchors=[focal_anchor])], frame
    )[occurrence]


def test_located_frame_keeps_primary_roles_and_exact_focal_input():
    layers, reference = frame_layer()
    signal = resolve("located-frame-2", layers, reference, "request")
    assert signal.rendered == "Predicate: approves\nArgument direct_object: the request"
    assert signal.omissions == ("Argument subject has no exact source location",)
    assert signal.report()["evidence"] == reference.values()
    query = ContextInput("occ", "source", "query", "request", TEXT, TEXT.index("request"), 33)
    baseline = render_context(query, E5, len)
    enriched = render_context(
        replace(
            query, representation_digest=signal.representation_digest, query_context=signal.rendered
        ),
        E5,
        len,
    )
    assert enriched.final_input_digest != baseline.final_input_digest
    assert enriched.text.startswith("Mention: request\n") and enriched.text.endswith(
        "Context: " + TEXT
    )
    assert (
        enriched.object_id == baseline.object_id
        and enriched.source_binding == baseline.source_binding
    )
    with pytest.raises(ValueError, match="does not locate"):
        resolve("located-frame-2", layers, reference, "request", pointer="#/texts/2")


@pytest.mark.parametrize("mutation", ["pin", "family", "kind", "projection", "missing"])
def test_primary_reference_cannot_select_foreign_or_unavailable_evidence(mutation):
    layers, reference = frame_layer()
    if mutation == "pin":
        reference = replace(reference, layer=replace(reference.layer, content_digest="f" * 64))
    elif mutation == "missing":
        reference = replace(reference, local_id="absent")
    else:
        report = layers[reference.layer]
        body = report.payload
        if mutation == "family":
            body["terms"][0]["family"] = "native.syntax"
        elif mutation == "kind":
            body["terms"][0]["kind"] = "operator"
        else:
            body["occurrences"][0]["extents"][0]["projection"] = "e" * 64
        report = LayerReport(canonical_bytes(body))
        pin = report.reference(reference.layer.task_id)
        reference = replace(reference, layer=pin)
        layers = {pin: report}
    with pytest.raises(ValueError):
        resolve("located-frame-2", layers, reference, "request")


def test_required_signal_cannot_be_truncated_into_an_ordinary_query():
    profile = replace(E5, max_tokens=55)
    baseline = ContextInput("occ", "source", "query", "request", TEXT, TEXT.index("request"), 33)
    assert render_context(baseline, profile, len).text.startswith("Mention: request\n")
    with pytest.raises(ContextCoreLimited, match="discriminating context"):
        render_context(
            replace(baseline, representation_digest="signal", query_context="Predicate: approves"),
            profile,
            len,
        )
    with pytest.raises(ValueError, match="representation identity"):
        replace(baseline, role="document", representation_digest="signal", query_context="added")


def test_local_descriptor_uses_retained_earlier_member_not_later_lookalike():
    members = [
        dict(
            local_id=str(i),
            kind="native.mention",
            family="maverick.mentions",
            literals=[literal],
            native_mention=dict(first=first, last=last, mapping_status="mapped"),
        )
        for i, (literal, first, last) in enumerate(
            (("A supervisor", 0, 1), ("She", 6, 6), ("Archive", 10, 10))
        )
    ]
    root = dict(
        local_id="cluster",
        kind="native.coreference_cluster",
        family="maverick.clusters",
        literals=["A supervisor", "She", "Archive"],
    )
    memberships = [
        dict(local_id=f"m{i}", group="cluster", member=m["local_id"], order=i)
        for i, m in enumerate(members)
    ]
    layers, reference = primary(root, members, memberships=memberships)
    signal = resolve("located-referent-2", layers, reference, "She")
    assert signal.rendered == "Earlier local mention: A supervisor"
    absent = resolve("located-referent-2", layers, reference, "supervisor")
    assert not absent.signals and not absent.representation_digest
    assert absent.omissions == ("no earlier local member has an exact source location",)


def test_discourse_uses_one_retained_adjacent_leaf_and_records_wider_omission():
    pieces = ("A supervisor approves the request.", "She files it.", "Archive it.")
    leaves = [
        dict(
            local_id=f"edu{i}",
            kind="native.edu",
            family="dipo.edus",
            literals=[piece],
            native_edu=dict(index=i),
        )
        for i, piece in enumerate(pieces)
    ]
    right = dict(
        local_id="right",
        kind="native.rst_node",
        family="dipo.rst",
        native_label="joint",
        literals=list(pieces[1:]),
        native_rst=dict(left_start=1, left_end=2, right_start=2, right_end=3, nuclearity="NN"),
    )
    root = dict(
        local_id="root",
        kind="native.rst_node",
        family="dipo.rst",
        native_label="elaboration",
        literals=list(pieces),
        native_rst=dict(left_start=0, left_end=1, right_start=1, right_end=3, nuclearity="NS"),
    )
    memberships = [
        dict(local_id=str(i), group=group, member=member, order=order)
        for i, (group, member, order) in enumerate(
            (("root", "edu0", 0), ("root", "right", 1), ("right", "edu1", 0), ("right", "edu2", 1))
        )
    ]
    layers, reference = primary(root, [right, *leaves], memberships=memberships)
    signal = resolve("located-discourse-neighbor-2", layers, reference, "files")
    assert signal.rendered == "Discourse neighbor: Archive it."
    assert signal.omissions == ("EDUs [0, 1]: wider_than_selected",)
    subtree = replace(reference, local_id="right")
    selected = resolve("located-discourse-neighbor-2", layers, subtree, "files")
    assert selected.rendered == "Discourse neighbor: Archive it."
    assert selected.omissions == ()


@pytest.mark.parametrize("guard", ["root", "member", "external", "site"])
def test_query_recipe_never_resolves_unselected_analytical_choices(guard):
    layers, reference = frame_layer()
    body = layers[reference.layer].payload
    if guard == "root":
        body["terms"][0]["required_choices"] = ["unselected"]
    elif guard == "member":
        body["terms"][1]["required_choices"] = ["unselected"]
    elif guard == "external":
        body["terms"][0]["required_external_choices"] = [reference.values()]
    else:
        body["terms"][0]["children"].append(dict(role="subject", choice_group="site"))
        body["choices"] = [dict(local_id="site", members=[])]
    report = LayerReport(canonical_bytes(body))
    pin = report.reference(reference.layer.task_id)
    with pytest.raises(ValueError, match=r"choice|reading"):
        resolve("located-frame-2", {pin: report}, replace(reference, layer=pin), "request")
