"""Registered native contextual evaluation over actual discovered primary reports."""

from dataclasses import replace

import pytest
from sqlalchemy import text

from corpus_structure.ingest.sentences import SentenceConfig
from corpus_structure.methods.native_profiles import spacy_selection
from corpus_structure.semantic.characterization_ports import contextual_operation_sources
from corpus_structure.semantic.composed import data_operation_dependencies
from corpus_structure.semantic.construction_products import construction_product_inputs
from corpus_structure.semantic.contextual_input_references import expand_selected_contextual_inputs
from corpus_structure.semantic.data_operation_service import (
    create_native_demand,
    execute_data_demand,
    read_data_demand,
)
from corpus_structure.semantic.data_operation_values import decode_semantic_value
from corpus_structure.semantic.primary_operations import combine_primary_sources
from corpus_structure.serve.demand_export import export_demand_result, verified_demand_export
from semantic.current_pdf_source_support import (
    PROJECT,
    ROOT,
    admit_current_target,
    current_consumer_request,
    current_pdf_recipe,
)
from semantic.data_operation_kernel_support import CapturedKernelInputs, split_captured_operations
from semantic.test_sentence_partition_chain_native import _registered_source


def contextual_recipe(directory):
    original = current_pdf_recipe(directory)
    captured = original.captured_inputs
    assert captured is not None
    dependencies, declarations, sources = split_captured_operations(captured)
    configuration = SentenceConfig(exclude=("ner", "lemmatizer"))
    installed = spacy_selection(configuration)
    sources = combine_primary_sources(
        sources,
        contextual_operation_sources(
            sentence_configuration=configuration,
            sentence_selection=installed,
        ),
    )
    return replace(
        original,
        name="registered-contextual-discovery",
        captured_inputs=CapturedKernelInputs(
            construction_product_inputs(captured.bundle),
            data_operation_dependencies(dependencies, declarations, sources),
            captured.profile,
        ),
    )


@pytest.mark.gpu
@pytest.mark.provider_evidence
def test_registered_contextual_evaluation_publishes_exact_role_addressed_graph(
    commit_db_engine, native_settings, tmp_path
):
    target = "text.contextual_evaluation/source-native"
    with _registered_source(
        commit_db_engine, native_settings, tmp_path, "All samples are finite."
    ) as source:
        kernel = admit_current_target(
            source,
            contextual_recipe(tmp_path / "recipe"),
            tmp_path / "consumer",
        )
        request = current_consumer_request(source, kernel, (target,), discover=True)
        with kernel.purpose("write").begin() as connection:
            registered = create_native_demand(connection, request, prepared=kernel.prepared)
        executed = execute_data_demand(
            kernel.purpose("write"),
            registered["demand_id"],
            source_root=ROOT / "python/corpus-structure/src",
            admission_engine=kernel.purpose("admit"),
            database_capacity=6,
        )
        with source.kernel.clone.admin.begin() as connection:
            snapshot = read_data_demand(
                connection,
                executed.demand_id,
                view="products",
                limit=1000,
                max_bytes=32 * 1024**2,
            )
            obligations = {row["obligation_id"]: row for row in snapshot["obligations"]}
            (use,) = [
                row
                for row in snapshot["uses"]
                if obligations[row["obligation_id"]]["operation_id"] == target
            ]
            assert use["fate"] == "fulfilled", use
            (product,) = [row for row in use["products"] if row["role"] == "result"]
            stored = decode_semantic_value(product["body"])
            original = {
                (row.role, str(row.position)): row.product_id
                for row in connection.execute(
                    text(
                        "SELECT role,position,product_id FROM ops.data_derivation_input "
                        "WHERE derivation_id=:episode"
                    ),
                    {"episode": use["derivation_id"]},
                )
            }
        assert "dependencies" not in stored
        assert stored["constructions_member_support"]
        assert all(
            role.collection == "set"
            for role in kernel.model.operation(target).roles
            if role.name in {"formal", "constructions", "supporting"}
        )
        archive = tmp_path / "contextual-export"
        with kernel.purpose("read").begin() as connection:
            exported = export_demand_result(
                connection,
                executed.demand_id,
                project_id=PROJECT,
                destination=archive,
                format="parquet",
                page_rows=16,
                page_bytes=32 * 1024**2,
                scope={"product_ids": [product["product_id"]]},
            )
        with verified_demand_export(archive, manifest_digest=exported.manifest_digest) as (
            manifest,
            _prepared,
            _models,
            index,
        ):
            retained = index.mapping("kb.data_product", ("id",))[product["product_id"]]
            assert decode_semantic_value(retained["canonical_body"]) == stored
            expanded = expand_selected_contextual_inputs(
                stored, index, manifest.cut_selection, product["product_id"]
            )
            members = {packet["member_id"]: packet["body"] for packet in expanded["members"]}
            expected = {}
            for role in ("formal", "constructions", "supporting"):
                for slot in stored[role + "_member_support"]:
                    target_ref = slot["target"]
                    parent = original[role, target_ref["occurrence"]]
                    assert (parent, target_ref["member_id"]) in index.mapping(
                        "kb.data_product_member", ("product_id", "member_id")
                    )
                    if slot["use"] in {"premise", "basis_premise"}:
                        body = members[slot["owner"]]
                        if slot["use"] == "basis_premise":
                            body = body["basis"]
                        expected[slot["owner"], slot["use"], slot["position"]] = dict(
                            product_id=parent, member_id=target_ref["member_id"]
                        )
                        assert (
                            body["external_premises"][slot["position"]]
                            == expected[slot["owner"], slot["use"], slot["position"]]
                        )
            assert expected
        resumed = execute_data_demand(
            kernel.purpose("write"),
            executed.demand_id,
            source_root=ROOT / "python/corpus-structure/src",
            admission_engine=kernel.purpose("admit"),
            database_capacity=6,
        )
        assert resumed.receipt_count == 0
