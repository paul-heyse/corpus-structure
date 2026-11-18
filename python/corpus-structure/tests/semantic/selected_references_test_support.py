"""Shared authored scenarios and fixtures for selected references test support."""

from typing import Any

from corpus_structure.semantic.demand_results import CutSelection
from corpus_structure.semantic.observations import source_value
from semantic.demand_result_support import demand_result_page


def reference_body() -> dict[str, Any]:
    source = demand_result_page()
    source.update(
        demand_id="demand:original-source",
        release_id="release:original-source",
        runtime_id="runtime:source",
        read_id="read:original-source",
    )
    cut = CutSelection.from_native(source)
    member = dict(
        product_id="product:source",
        member_id="source:one",
        subject="source",
        subject_definition="original-source-view",
        original_source="document:A",
        kind_contract="kind:source",
        analyzed_scope_meaning='["mapping",[]]',
    )
    return dict(
        retained_correspondence=source_value(None),
        reference_name="independent-question",
        author="independent operator",
        pass_kind="C",
        direction="source_first",
        source_demand_id=source["demand_id"],
        source_cut_id=cut.identity,
        source_read_id=source["read_id"],
        source_cut=source_value(cut.record),
        source_release_id=source["release_id"],
        source_runtime_id=source["runtime_id"],
        source_members=[member],
        output_members=[],
        cases=[
            dict(
                case_id="case:root",
                opportunity_id="opportunity:source",
                question="Which retained kind does the source express?",
                matcher="fields",
                source_members=[member],
                expected=source_value({"value": {"kind": "predicate"}}),
                judgment="supported",
            )
        ],
    )
