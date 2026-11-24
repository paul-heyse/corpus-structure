"""Discovery consumes exact computational views; raw originals retain factual custody."""

from dataclasses import replace

import pytest
from sqlalchemy.exc import DBAPIError

from corpus_structure.semantic.data_operation_demands import (
    DemandPlanner,
    DiscoverySelection,
    OperationSelection,
    freeze_demand,
)
from corpus_structure.semantic.data_operation_json import json_bytes
from corpus_structure.semantic.data_operation_service import execute_data_demand
from corpus_structure.semantic.data_operation_source_sets import FrozenSourceSet
from corpus_structure.semantic.data_operation_storage import DataOperationStorage
from corpus_structure.semantic.data_operation_values import decode_semantic_value
from corpus_structure.semantic.demand_results import acquired_selected_relations, read_demand_result
from corpus_structure.semantic.original_documents import acquire_original_document_selection
from semantic.current_pdf_source_support import (
    PROJECT,
    ROOT,
    selected_current_sources,
    source_entry,
)
from semantic.current_pdf_source_support import (
    current_pdf_source as current_pdf_source,
)


@pytest.mark.parametrize(
    "complete,views",
    [(True, False), (False, False), (True, True)],
    ids=["closed-empty", "partial-empty", "closed-computational-views"],
)
def test_actual_source_discovery_closure_and_scoped_child_publication(
    current_pdf_source, complete, views, tmp_path
):
    case, kernel = current_pdf_source, current_pdf_source.kernel
    members = [row for row, _ in selected_current_sources(case)]
    assert members, "actual native PDF discovery must publish genuine selected source members"
    selected = members if views else []
    with kernel.purpose("write").begin() as connection:
        document_key = case.document_key
        if not views:
            from hashlib import sha256

            from corpus_structure.core.evidence import document_key as original_key
            from corpus_structure.semantic.original_documents import register_original_document

            path = tmp_path / "uncaptured.pdf"
            path.write_bytes(case.original)
            register_original_document(
                connection,
                prepared=kernel.prepared,
                project_id=PROJECT,
                source_uri="uncaptured.pdf",
                original_path=str(path),
                original=case.original,
                mime="application/pdf",
            )
            path.unlink()
            document_key = original_key(
                PROJECT, "uncaptured.pdf", sha256(case.original).hexdigest()
            )
        original = acquire_original_document_selection(
            connection, project_id=PROJECT, document_key=document_key
        )
        intent = freeze_demand(
            kernel.model,
            roots=(original.root,),
            targets=("source.selected_views/discovery",),
            selections=(
                OperationSelection(
                    "source.selected_views/discovery", parameters=json_bytes({"complete": complete})
                ),
            ),
            discovery=(
                DiscoverySelection(
                    "source.selected_views/discovery",
                    "result",
                    "profile.segments/source-native",
                    "selected-source-views",
                    target_role="source",
                ),
            ),
            original_sources=(original.selection(),),
            source_sets=(
                FrozenSourceSet.from_selected(
                    "selected-source-views", tuple(source_entry(row) for row in selected)
                ),
            ),
            inference="source-discovery-control",
            execution_profile=kernel.recipe.execution_profile,
        )
        planner = DemandPlanner(kernel.model, DataOperationStorage(connection))
        invalid = intent.record
        invalid["discovery"][0]["target_role"] = "not-an-input"
        with pytest.raises(DBAPIError) as refusal, connection.begin_nested():
            planner.register(
                replace(intent, content=json_bytes(invalid)),
                project=PROJECT,
                release=kernel.prepared.release_id,
                runtime=kernel.runtime,
            )
        cause = refusal.value.orig
        assert getattr(cause, "sqlstate", None) == "P0001"
        assert getattr(getattr(cause, "diag", None), "message_primary", None) == (
            "discovery target role differs from declared member/input contracts"
        )
        demand = planner.register(
            intent, project=PROJECT, release=kernel.prepared.release_id, runtime=kernel.runtime
        )["demand_id"]
    execute_data_demand(
        kernel.purpose("write"),
        demand,
        source_root=ROOT / "python/corpus-structure/src",
        project_id=PROJECT,
        admission_engine=kernel.purpose("admit"),
        database_capacity=6,
    )
    with kernel.purpose("read").begin() as connection:
        page = read_demand_result(connection, demand, project_id=PROJECT)
        assert page.continuation is None
        obligations = [
            row
            for row in page.record["obligations"]
            if row["operation_id"] == "profile.segments/source-native"
        ]
        assert len(obligations) == len(selected)
        (population,) = page.record["populations"]
        assert population["complete"] is complete
        assert len(population["members"]) == len(selected)
        with acquired_selected_relations(
            connection,
            demand,
            project_id=PROJECT,
            scope={},
            read_id=page.cut.record["read_id"],
            expected_cut=page.cut.identity,
            capture_frontier=True,
        ) as (_, index):
            child_uses = [
                row
                for row in index.frontier_rows("uses")
                if row["obligation_id"] in {row["obligation_id"] for row in obligations}
            ]
            assert len(child_uses) == len(selected) and all(
                row["fate"] == "fulfilled" for row in child_uses
            )
            outputs = [
                edge
                for use in child_uses
                for edge in index.rows_for(
                    "ops.data_derivation_output", derivation_id=use["derivation_id"]
                )
            ]
            products = index.mapping("kb.data_product", ("id",))
            bodies = [
                decode_semantic_value(products[row["product_id"]]["canonical_body"])
                for row in outputs
            ]
            assert sorted(body["chars"] for body in bodies) == sorted(
                len(row["body"]["text"]) for row in selected
            )
            # The only original facts remain actual document references. Selected views
            # have producing episodes and cannot be recast as original admissions.
            assert all(
                row["reference"]["kind"] == "original-document"
                for row in index.rows("ops.original_source_admission")
            )
