"""Current selected-member inputs for independent contextual query criteria."""

from copy import deepcopy

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
from corpus_structure.semantic.source_contexts import record_source_pin
from corpus_structure.semantic.source_products import native_projection_identity

TEXT = "A supervisor approves the request. She files it. Archive it."
POINTER = "#/texts/1"


def source(text=TEXT):
    items = [dict(self_ref=POINTER, label="text", text=text)]
    pieces = [
        dict(kind="native_text", item_ref=POINTER, source_field="text", start=0, end=len(text))
    ]
    projection = native_projection_identity(text, pieces, items, (), ())
    coordinate = dict(
        document="document:A", projection=projection, section_pointer=POINTER, membership="direct"
    )
    selectors = [dict(projection=projection, native_pointer=POINTER, start=0, end=len(text))]
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
            subject_definition="original-source-view",
        ),
        "product:source",
        "member:source",
        "kind:source",
    )
    return DeclaredNativeFrameSource(
        canonical_bytes(
            dict(source=coordinate, selectors=selectors, text=text, items=items, pieces=pieces)
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
            start = frame.text.index(literal)
            row["occurrences"].append(local)
            occurrences.append(
                dict(
                    local_id=local,
                    extents=[
                        dict(
                            projection=frame.projection_digest,
                            native_pointer=next(
                                piece["item_ref"]
                                for piece in frame.value["pieces"]
                                if piece["kind"] == "native_text"
                            ),
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
        frame or source(),
        root,
        [
            dict(local_id="predicate", literals=["approves"], status="interpreted"),
            dict(local_id="object", literals=["the request"], status="interpreted"),
            dict(local_id="unknown", status="unknown"),
        ],
    )
