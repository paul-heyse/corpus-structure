"""Independent finite primary context cases shared by controlled and provider tests."""

from types import SimpleNamespace

from methods.contextual_query_support import TEXT, primary, source

from corpus_structure.semantic.contributions import occurrence_identity
from corpus_structure.semantic.data_operation_json import json_bytes
from corpus_structure.semantic.data_operation_model import (
    BoundRoleMember,
    ResolvedRoleBinding,
    SubjectContext,
)
from corpus_structure.semantic.data_operation_source_sets import (
    FrozenSourceSet,
    SourceSetEntry,
    source_sets_record,
)
from corpus_structure.semantic.data_operation_support import ComputationalSupportReference
from corpus_structure.semantic.record_contracts import anchor_identity
from corpus_structure.semantic.source_contexts import record_source_pin


def case(recipe, *, frame=None):
    frame = frame or source()
    pointer = next(
        piece["item_ref"] for piece in frame.value["pieces"] if piece["kind"] == "native_text"
    )
    if recipe == "located-frame-2":
        layers, ref = primary(
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
                ],
            ),
            [
                dict(local_id="predicate", literals=["approves"], status="interpreted"),
                dict(local_id="object", literals=["the request"], status="interpreted"),
            ],
        )
        focal, expected = "request", "Predicate: approves\nArgument direct_object: the request"
    elif recipe == "located-referent-2":
        layers, ref = primary(
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
        focal, expected = "She", "Earlier local mention: A supervisor"
    else:
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
                (
                    ("root", "edu0", 0),
                    ("root", "right", 1),
                    ("right", "edu1", 0),
                    ("right", "edu2", 1),
                )
            )
        ]
        layers, ref = primary(frame, root, [right, *leaves], memberships)
        focal, expected = "files", "Discourse neighbor: Archive it."
    payload = layers[ref.product].payload
    packets = [
        dict(
            member_id=row["local_id"],
            kind_contract="kind:" + tag,
            context={},
            body=dict(row, record_type=tag),
        )
        for collection, tag in (
            ("occurrences", "occurrence"),
            ("annotations", "annotation"),
            ("memberships", "membership"),
            ("terms", "term"),
        )
        for row in payload[collection]
    ]
    body = dict(
        source=payload["source"], selectors=payload["selectors"], members=packets, dependencies=[]
    )
    start = TEXT.index(focal)
    anchor = dict(
        pin=record_source_pin(frame),
        space="native",
        pointer=pointer,
        precision="exact",
        start=start,
        end=start + len(focal),
        source_piece=focal,
    )
    anchor["anchor_id"] = anchor_identity(anchor)
    occurrence = dict(
        kind="occurrence",
        semantic_type="contextual.located_mention",
        contribution_id="source-contribution:" + "a" * 64,
        operation_key="operation:actual-source",
        occurrence_id=occurrence_identity((anchor,)),
        pin=record_source_pin(frame),
        anchors=[anchor],
    )
    context = SubjectContext(
        "project:A", "source:A", "document:A", b"{}", subject_definition="original-source-view"
    )
    member = BoundRoleMember(
        ref.product.product_id,
        "kind:primary",
        context.subject,
        context.original_source,
        context.analyzed_scope,
        b"{}",
        ("episode:primary",),
        b"{}",
        subject_definition="original-source-view",
        position=0,
        support_references=tuple(
            ComputationalSupportReference(derivation_id=episode) for episode in ("episode:primary",)
        ),
    )
    sources = source_sets_record(
        (
            FrozenSourceSet(
                "query-context-primary",
                (SourceSetEntry.from_semantic_source(ref.product, context=context),),
            ),
        )
    )
    binding = SimpleNamespace(
        roles=(ResolvedRoleBinding("primary", "present", (member,)),),
        source_sets=json_bytes(sources),
        subject_context=context,
    )
    return frame, occurrence, (body,), binding, ref, expected
