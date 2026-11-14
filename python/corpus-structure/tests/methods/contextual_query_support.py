"""Controlled inputs and builders shared by the contextual query consumers."""

from hashlib import sha256

from corpus_structure.semantic.characterization import AnnotationReference, LayerReport
from corpus_structure.semantic.identity import canonical_bytes
from corpus_structure.semantic.product_reference import ProductReference
from corpus_structure.semantic.proposals import NativeFrameSource
from corpus_structure.semantic.record_contracts import anchor_identity
from corpus_structure.semantic.source_contexts import record_source_pin

TEXT = "A supervisor approves the request. She files it. Archive it."


POINTER = "#/texts/1"


def source(text=TEXT):
    pieces = [dict(kind="native_text", item_ref=POINTER, start=0, end=len(text))]
    context = dict(
        pieces=pieces, items=[dict(self_ref=POINTER, text=text)], ancestors=[], health={}
    )
    projection = dict(text=text, pieces=pieces, items=[POINTER], ancestors=[], health={})
    return NativeFrameSource(
        "source",
        text,
        (),
        1,
        ProductReference(1, "native", "a" * 64),
        "#/groups/0",
        "direct",
        sha256(canonical_bytes(projection)).hexdigest(),
        "c" * 64,
        canonical_bytes(context).decode(),
    )


def anchor(literal, *, frame=None, pointer=POINTER):
    frame = frame or source()
    start = frame.text.index(literal)
    row = dict(
        pin=record_source_pin(frame),
        space="native",
        pointer=pointer,
        precision="exact",
        start=start,
        end=start + len(literal),
        source_piece=literal,
    )
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
            occurrences.append(
                dict(
                    local_id=key,
                    extents=[
                        dict(
                            source_view_id=frame.source_view_id,
                            projection=frame.projection_digest,
                            start=start,
                            end=start + len(literal),
                        )
                    ],
                )
            )
    terms = rows if root["kind"] == "predicate" else []
    report = LayerReport(
        canonical_bytes(
            dict(
                base_document=frame.native_product.values(),
                source_scope={"source_view_ids": [frame.source_view_id]},
                terms=terms,
                annotations=[] if terms else rows,
                occurrences=occurrences,
                memberships=list(memberships),
                choices=[],
                dependencies=[],
            )
        )
    )
    pin = report.reference(3)
    return {pin: report}, AnnotationReference(pin, root["local_id"])


def frame_layer(*, frame=None):
    root = dict(
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
    )
    return primary(
        root,
        [
            dict(local_id="predicate", literals=["approves"], status="interpreted"),
            dict(local_id="object", literals=["the request"], status="interpreted"),
            dict(local_id="unknown", status="unknown"),
        ],
        frame=frame,
    )
