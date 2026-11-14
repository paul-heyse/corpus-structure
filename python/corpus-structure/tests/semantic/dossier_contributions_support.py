"""Shared controlled inputs and builders for dossier contributions support."""

import json

from methods.m1_source_preparation_support import native_table_source, table_cell
from methods.scoped_relations_support import complete_native_fields, discover_relations

from corpus_structure.semantic.observations import source_python
from corpus_structure.semantic.proposals import native_source_frame
from corpus_structure.semantic.retained_contributions import RetainedContributionRef
from corpus_structure.semantic.source_contexts import record_source_pin
from corpus_structure.semantic.structural_products import (
    ExternalSourceRef,
    StructuralInput,
    StructuralPassage,
)


def source_fixture():
    frame = native_source_frame(
        complete_native_fields(
            native_table_source(
                (
                    table_cell("Probability %", 0, 1, column_header=True),
                    table_cell("50", 1, 1),
                )
            )
        ),
        (),
    )
    rows = discover_relations(frame)["contributions"]
    relation = next(
        r
        for r in rows
        if r["kind"] == "relation" and source_python(r["value"])["relation"] == "unit"
    )
    ids = set(relation["members"]) | {relation["contribution_id"]}
    closure = [r for r in rows if r["contribution_id"] in ids]
    pin = record_source_pin(frame)
    source = ExternalSourceRef(
        project_id="p",
        run_id=1,
        cut_id=1,
        release_id="r",
        result_revision=1,
        source_view_id=pin["source_view_id"],
        native_task_id=pin["native_product_task_id"],
        native_product_key=pin["product_key"],
        native_content_digest=pin["product_digest"],
        projection_digest=pin["projection_digest"],
        recipe_digest=pin["recipe_digest"],
        coordinate_version=3,
    )
    inputs = StructuralInput(
        question="Structure corpus",
        scope="corpus",
        inventory_id="i",
        policy_id="p",
        sources=(source,),
        passages=(
            StructuralPassage(
                passage_id="table",
                source_ref=source.identity,
                start=0,
                end=len(frame.text),
                text=frame.text,
                scope="table",
            ),
        ),
        dependencies=(relation["contribution_id"],),
    )
    ref = RetainedContributionRef(
        contribution_id=relation["contribution_id"],
        project_id="p",
        run_id=1,
        cut_id=1,
        release_id="r",
        result_revision=1,
        selected_task_id=1,
        origin_task_id=1,
        runtime_fingerprint="runtime",
    )
    native = json.loads(frame.native_context)
    payload = dict(
        contributions=closure,
        sources=[
            dict(
                source_view_id=frame.source_view_id,
                pin=pin,
                projection=dict(text=frame.text, pieces=native["pieces"]),
            )
        ],
    )
    return inputs, ref, payload
