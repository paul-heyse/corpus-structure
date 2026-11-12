"""Primary-node identity, exact native positions and bounded retrieval signals."""

from dataclasses import replace
from hashlib import sha256

import pytest

from corpus_structure.methods.contextual_embeddings import E5, ContextCoreLimited, ContextInput, render_context
from corpus_structure.methods.contextual_query import QueryContextSelection, resolve_query_contexts
from corpus_structure.semantic.characterization import AnnotationReference, LayerReport
from corpus_structure.semantic.contributions import occurrence_identity
from corpus_structure.semantic.identity import canonical_bytes
from corpus_structure.semantic.product_reference import ProductReference
from corpus_structure.semantic.proposals import NativeFrameSource
from corpus_structure.semantic.record_contracts import anchor_identity
from corpus_structure.semantic.source_contexts import record_source_pin

TEXT = "A supervisor approves the request. She files it. Archive it."
POINTER = "#/texts/1"


def source(text=TEXT):
    pieces = [dict(kind="native_text", item_ref=POINTER, start=0, end=len(text))]
    context = dict(pieces=pieces, items=[dict(self_ref=POINTER, text=text)], ancestors=[], health={})
    projection = dict(text=text, pieces=pieces, items=[POINTER], ancestors=[], health={})
    return NativeFrameSource(
        "source", text, (), 1, ProductReference(1, "native", "a" * 64), "#/groups/0", "direct",
        sha256(canonical_bytes(projection)).hexdigest(), "c" * 64, canonical_bytes(context).decode(),
    )


def anchor(literal, *, frame=None, pointer=POINTER):
    frame = frame or source()
    start = frame.text.index(literal)
    row = dict(pin=record_source_pin(frame), space="native", pointer=pointer, precision="exact",
               start=start, end=start+len(literal), source_piece=literal)
    return dict(row, anchor_id=anchor_identity(row))


def primary(root, members, *, frame=None, memberships=()):
    frame = frame or source()
    rows = [root, *members]
    occurrences = []
    for row in rows:
        row.setdefault("occurrences", [])
        for index, literal in enumerate(row.pop("literals", ())):
            start = frame.text.index(literal)
            key = f"{row['local_id']}:occ:{index}"
            row["occurrences"].append(key)
            occurrences.append(dict(local_id=key, extents=[dict(
                source_view_id=frame.source_view_id, projection=frame.projection_digest,
                start=start, end=start+len(literal),
            )]))
    terms = rows if root["kind"] == "predicate" else []
    report = LayerReport(canonical_bytes(dict(
        base_document=frame.native_product.values(), source_scope={"source_view_ids":[frame.source_view_id]},
        terms=terms, annotations=[] if terms else rows, occurrences=occurrences,
        memberships=list(memberships), choices=[], dependencies=[],
    )))
    pin = report.reference(3)
    return {pin:report}, AnnotationReference(pin,root["local_id"])


def frame_layer(*, frame=None):
    root = dict(local_id="frame", kind="predicate", family="construction.source_readings",
                vocabulary="source-linguistic-rules-1", literals=["A supervisor approves the request."],
                children=[dict(role="predicate",target="predicate"),dict(role="direct_object",target="object"),
                          dict(role="subject",target="unknown")])
    return primary(root, [
        dict(local_id="predicate", literals=["approves"],status="interpreted"),
        dict(local_id="object",literals=["the request"],status="interpreted"),
        dict(local_id="unknown",status="unknown"),
    ],frame=frame)


def resolve(recipe, layers, reference, focal, *, frame=None, pointer=POINTER):
    frame = frame or source()
    focal_anchor=anchor(focal,frame=frame,pointer=pointer)
    occurrence=occurrence_identity((focal_anchor,))
    selection=QueryContextSelection.model_validate(dict(
        recipe=recipe,bindings=[dict(occurrence_id=occurrence,evidence=reference.values())],
    ))
    return resolve_query_contexts(selection,layers,[dict(occurrence_id=occurrence,anchors=[focal_anchor])],frame)[occurrence]


def test_located_frame_keeps_primary_roles_and_exact_focal_input():
    layers, reference=frame_layer()
    signal=resolve("located-frame-2",layers,reference,"request")
    assert signal.rendered == "Predicate: approves\nArgument direct_object: the request"
    assert signal.omissions == ("Argument subject has no exact source location",)
    assert signal.report()["evidence"] == reference.values()
    query=ContextInput("occ","source","query","request",TEXT,TEXT.index("request"),33)
    baseline=render_context(query,E5,len)
    enriched=render_context(replace(query,representation_digest=signal.representation_digest,query_context=signal.rendered),E5,len)
    assert enriched.final_input_digest != baseline.final_input_digest
    assert enriched.text.startswith("Mention: request\n") and enriched.text.endswith("Context: "+TEXT)
    assert enriched.object_id == baseline.object_id and enriched.source_binding == baseline.source_binding
    with pytest.raises(ValueError,match="does not locate"):
        resolve("located-frame-2",layers,reference,"request",pointer="#/texts/2")


@pytest.mark.parametrize("mutation",["pin","family","kind","projection","missing"])
def test_primary_reference_cannot_select_foreign_or_unavailable_evidence(mutation):
    layers,reference=frame_layer()
    if mutation=="pin":
        reference=replace(reference,layer=replace(reference.layer,content_digest="f"*64))
    elif mutation=="missing":
        reference=replace(reference,local_id="absent")
    else:
        report=layers[reference.layer]; body=report.payload
        if mutation=="family":body["terms"][0]["family"]="native.syntax"
        elif mutation=="kind":body["terms"][0]["kind"]="operator"
        else:body["occurrences"][0]["extents"][0]["projection"]="e"*64
        report=LayerReport(canonical_bytes(body));pin=report.reference(reference.layer.task_id)
        reference=replace(reference,layer=pin);layers={pin:report}
    with pytest.raises(ValueError):resolve("located-frame-2",layers,reference,"request")


def test_required_signal_cannot_be_truncated_into_an_ordinary_query():
    profile=replace(E5,max_tokens=55)
    baseline=ContextInput("occ","source","query","request",TEXT,TEXT.index("request"),33)
    assert render_context(baseline,profile,len).text.startswith("Mention: request\n")
    with pytest.raises(ContextCoreLimited,match="discriminating context"):
        render_context(replace(baseline,representation_digest="signal",query_context="Predicate: approves"),profile,len)
    with pytest.raises(ValueError,match="representation identity"):
        replace(baseline,role="document",representation_digest="signal",query_context="added")


def test_local_descriptor_uses_retained_earlier_member_not_later_lookalike():
    members=[dict(local_id=str(i),kind="native.mention",family="maverick.mentions",literals=[literal],
                  native_mention=dict(first=first,last=last,mapping_status="mapped"))
             for i,(literal,first,last) in enumerate((("A supervisor",0,1),("She",6,6),("Archive",10,10)))]
    root=dict(local_id="cluster",kind="native.coreference_cluster",family="maverick.clusters",
              literals=["A supervisor","She","Archive"])
    memberships=[dict(local_id=f"m{i}",group="cluster",member=m["local_id"],order=i) for i,m in enumerate(members)]
    layers,reference=primary(root,members,memberships=memberships)
    signal=resolve("located-referent-2",layers,reference,"She")
    assert signal.rendered == "Earlier local mention: A supervisor"
    absent=resolve("located-referent-2",layers,reference,"supervisor")
    assert not absent.signals and not absent.representation_digest
    assert absent.omissions == ("no earlier local member has an exact source location",)


def test_discourse_uses_one_retained_adjacent_leaf_and_records_wider_omission():
    pieces=("A supervisor approves the request.","She files it.","Archive it.")
    leaves=[dict(local_id=f"edu{i}",kind="native.edu",family="dipo.edus",literals=[piece],native_edu=dict(index=i)) for i,piece in enumerate(pieces)]
    right=dict(local_id="right",kind="native.rst_node",family="dipo.rst",native_label="joint",literals=list(pieces[1:]),native_rst=dict(left_start=1,left_end=2,right_start=2,right_end=3,nuclearity="NN"))
    root=dict(local_id="root",kind="native.rst_node",family="dipo.rst",native_label="elaboration",literals=list(pieces),native_rst=dict(left_start=0,left_end=1,right_start=1,right_end=3,nuclearity="NS"))
    memberships=[dict(local_id=str(i),group=group,member=member,order=order) for i,(group,member,order) in enumerate((("root","edu0",0),("root","right",1),("right","edu1",0),("right","edu2",1)))]
    layers,reference=primary(root,[right,*leaves],memberships=memberships)
    signal=resolve("located-discourse-neighbor-2",layers,reference,"files")
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
    with pytest.raises(ValueError, match="choice|reading"):
        resolve("located-frame-2", {pin: report}, replace(reference, layer=pin), "request")
