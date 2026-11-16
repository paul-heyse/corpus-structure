"""Actual declared source joins for private dossier membership controls."""

from methods.m1_source_preparation_support import native_table_source, table_cell
from methods.scoped_relations_support import discover_relations

from corpus_structure.semantic.declared_structural_references import (
    DeclaredContributionRef,
    DeclaredStructuralSource,
)
from corpus_structure.semantic.observations import source_python
from corpus_structure.semantic.structural_products import DeclaredStructuralInput, StructuralPassage


def source_fixture():
    frame = native_table_source(
        (table_cell("Probability %", 0, 1, column_header=True), table_cell("50", 1, 1))
    )
    rows = discover_relations(frame, annotations=())["contributions"]
    relation = next(
        row
        for row in rows
        if row["kind"] == "relation" and source_python(row["value"])["relation"] == "unit"
    )
    ids = set(relation["members"]) | {relation["contribution_id"]}
    closure = [row for row in rows if row["contribution_id"] in ids]
    pin = frame.pin.values()
    source = DeclaredStructuralSource.model_validate(pin)
    inputs = DeclaredStructuralInput(
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
    ref = DeclaredContributionRef(
        contribution_id=relation["contribution_id"],
        product_id="unadmitted:source-joins",
        kind_contract="unadmitted:retained-contributions",
        project_id=pin["project_id"],
        subject=pin["subject"],
        subject_definition=pin["subject_definition"],
        original_source=pin["original_source"],
        analyzed_scope_meaning=pin["analyzed_scope_meaning"],
    )
    payload = dict(contributions=closure, sources=[dict(pin=pin, projection=frame.value)])
    return inputs, ref, payload
