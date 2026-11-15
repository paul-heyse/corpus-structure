"""Independent target-member query12 recipes with no task/layer address adapters."""

from copy import deepcopy

import pytest

from corpus_structure.methods.contextual_query import (
    DeclaredQueryContextBinding,
    DeclaredQueryContextSelection,
    resolve_query_contexts,
)
from corpus_structure.semantic.contributions import occurrence_identity
from corpus_structure.semantic.data_operation_model import SubjectContext
from corpus_structure.semantic.data_product_reference import (
    DataProductMemberReference,
    DataProductReference,
)
from corpus_structure.semantic.declared_formal_readings import DeclaredFormalInventory
from corpus_structure.semantic.declared_record_sources import (
    DeclaredNativeFrameSource,
    DeclaredRecordSource,
)
from corpus_structure.semantic.identity import canonical_bytes
from corpus_structure.semantic.record_contracts import anchor_identity
from corpus_structure.semantic.source_contexts import PreparedNativeSources, record_source_pin
from corpus_structure.semantic.source_products import native_projection_identity

TEXT = "A supervisor approves the request. She files it. Archive it."
POINTER = "#/texts/1"


def source():
    items = [dict(self_ref=POINTER, label="text", text=TEXT)]
    pieces = [
        dict(kind="native_text", item_ref=POINTER, source_field="text", start=0, end=len(TEXT))
    ]
    projection = native_projection_identity(TEXT, pieces, items, (), ())
    coordinate = dict(
        document="document:A", projection=projection, section_pointer=POINTER, membership="direct"
    )
    selectors = [dict(projection=projection, native_pointer=POINTER, start=0, end=len(TEXT))]
    address = DeclaredRecordSource(
        "document:A",
        projection,
        POINTER,
        "direct",
        SubjectContext(
            "project:A",
            "source:A",
            "document:A",
            canonical_bytes({"source": coordinate, "selectors": selectors}),
        ),
        "product:source",
        "member:source",
        "kind:source",
    )
    return DeclaredNativeFrameSource(
        canonical_bytes(
            dict(source=coordinate, selectors=selectors, text=TEXT, items=items, pieces=pieces)
        ).decode(),
        canonical_bytes(address.pin()).decode(),
    )


def primary(frame, root, children, memberships=()):
    rows = deepcopy([root, *children])
    occurrences = []
    for row in rows:
        row["occurrences"] = []
        for ordinal, literal in enumerate(row.pop("literals", ())):
            local = row["local_id"] + ":occ:" + str(ordinal)
            start = TEXT.index(literal)
            row["occurrences"].append(local)
            occurrences.append(
                dict(
                    local_id=local,
                    extents=[
                        dict(
                            projection=frame.projection_digest,
                            native_pointer=POINTER,
                            start=start,
                            end=start + len(literal),
                        )
                    ],
                )
            )
    reference = DataProductReference("product:primary")
    terms = rows if root["kind"] == "predicate" else []
    payload = dict(
        source=frame.value["source"],
        selectors=frame.value["selectors"],
        terms=terms,
        annotations=[] if terms else rows,
        occurrences=occurrences,
        memberships=list(memberships),
        choices=[],
        dependencies=[],
    )
    inventory = DeclaredFormalInventory(reference, canonical_bytes(payload))
    return {reference: inventory}, DataProductMemberReference(reference, root["local_id"])


def resolve(recipe, layers, reference, focal, frame):
    start = TEXT.index(focal)
    anchor = dict(
        pin=record_source_pin(frame),
        space="native",
        pointer=POINTER,
        precision="exact",
        start=start,
        end=start + len(focal),
        source_piece=focal,
    )
    anchor["anchor_id"] = anchor_identity(anchor)
    occurrence = occurrence_identity((anchor,))
    selection = DeclaredQueryContextSelection(
        recipe, (DeclaredQueryContextBinding(occurrence, reference),)
    )
    return resolve_query_contexts(
        selection,
        layers,
        [dict(occurrence_id=occurrence, anchors=[anchor])],
        frame,
        preparation=PreparedNativeSources((frame,)),
    )[occurrence]


def test_declared_frame_recipe_retains_real_semantic_reference_and_endpoint_roles():
    frame = source()
    layers, reference = primary(
        frame,
        dict(
            local_id="frame",
            kind="predicate",
            family="construction.source_readings",
            vocabulary="source-linguistic-rules-1",
            literals=["A supervisor approves the request."],
            children=[
                dict(role="predicate", target="predicate"),
                dict(role="direct_object", target="object"),
                dict(role="subject", target="unknown"),
            ],
        ),
        [
            dict(local_id="predicate", literals=["approves"], status="interpreted"),
            dict(local_id="object", literals=["the request"], status="interpreted"),
            dict(local_id="unknown", status="unknown"),
        ],
    )
    result = resolve("located-frame-2", layers, reference, "request", frame)
    assert result.rendered == "Predicate: approves\nArgument direct_object: the request"
    assert result.omissions == ("Argument subject has no exact source location",)
    assert result.report()["evidence"] == {"product_id": "product:primary", "member_id": "frame"}
    assert all(
        signal.anchors[0]["pin"]["source_product"] == "product:source" for signal in result.signals
    )
    assert "task_id" not in canonical_bytes(result.report()).decode()
    body = layers[reference.product].payload
    body["terms"][1]["required_external_choices"] = [
        {"product_id": "product:foreign", "member_id": "choice"}
    ]
    layers = {reference.product: DeclaredFormalInventory(reference.product, canonical_bytes(body))}
    with pytest.raises(ValueError, match="choice"):
        resolve("located-frame-2", layers, reference, "request", frame)


def test_declared_referent_recipe_keeps_earlier_local_mention_without_inference():
    frame = source()
    layers, reference = primary(
        frame,
        dict(
            local_id="cluster",
            kind="native.coreference_cluster",
            family="maverick.clusters",
            literals=["A supervisor", "She"],
        ),
        [
            dict(
                local_id="first",
                kind="native.mention",
                family="maverick.mentions",
                literals=["A supervisor"],
                native_mention=dict(first=0, last=1, mapping_status="mapped"),
            ),
            dict(
                local_id="second",
                kind="native.mention",
                family="maverick.mentions",
                literals=["She"],
                native_mention=dict(first=6, last=6, mapping_status="mapped"),
            ),
        ],
        [
            dict(local_id="link1", group="cluster", member="first", order=0),
            dict(local_id="link2", group="cluster", member="second", order=1),
        ],
    )
    result = resolve("located-referent-2", layers, reference, "She", frame)
    assert result.rendered == "Earlier local mention: A supervisor"
    assert result.evidence == reference


def test_declared_discourse_recipe_keeps_intermediate_tree_and_native_direction():
    frame = source()
    pieces = ["A supervisor approves the request.", "She files it.", "Archive it."]
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
    root = dict(
        local_id="root",
        kind="native.rst_node",
        family="dipo.rst",
        native_label="elaboration",
        literals=pieces,
        native_rst=dict(left_start=0, left_end=1, right_start=1, right_end=3, nuclearity="NS"),
    )
    right = dict(
        local_id="right",
        kind="native.rst_node",
        family="dipo.rst",
        native_label="joint",
        literals=pieces[1:],
        native_rst=dict(left_start=1, left_end=2, right_start=2, right_end=3, nuclearity="NN"),
    )
    memberships = [
        dict(local_id=str(i), group=group, member=member, order=order)
        for i, (group, member, order) in enumerate(
            (("root", "edu0", 0), ("root", "right", 1), ("right", "edu1", 0), ("right", "edu2", 1))
        )
    ]
    layers, reference = primary(frame, root, [right, *leaves], memberships)
    result = resolve("located-discourse-neighbor-2", layers, reference, "files", frame)
    assert result.rendered == "Discourse neighbor: Archive it."
    assert result.omissions == ("EDUs [0, 1]: wider_than_selected",)
    body = layers[reference.product].payload
    body["memberships"] = body["memberships"][:-1]
    with pytest.raises(ValueError, match="complete"):
        resolve(
            "located-discourse-neighbor-2",
            {reference.product: DeclaredFormalInventory(reference.product, canonical_bytes(body))},
            reference,
            "files",
            frame,
        )
