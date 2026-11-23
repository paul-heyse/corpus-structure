"""Two genuine formal calculations retain distinct custody in ordinary construction."""

import pytest

from corpus_structure.semantic.data_operation_service import DemandOperationSelection
from corpus_structure.semantic.data_operation_source_sets import (
    FrozenSourceSet,
    SelectedSourceSetEntry,
    source_sets_record,
)
from corpus_structure.semantic.demand_results import read_demand_result, stream_selected_support
from corpus_structure.serve.demand_export import export_demand_result, verified_demand_export
from semantic.current_pdf_source_support import (
    PROJECT,
    PdfSourceScenario,
    admit_current_target,
    current_consumer_request,
    section_content,
)
from semantic.structural_admission_native_support import execute
from semantic.test_sentence_partition_chain_native import _recipe, _registered_source

FORMAL = "text.formal_evidence/source-native"
CONSTRUCTION = "text.constructions/source-native"
FORMAL_KIND = (
    "https://corpus-structure.dev/semantic/data-operation-characterization/DdoFormalProduct"
)
CONSTRUCTION_KIND = "https://corpus-structure.dev/semantic/data-operation-constructions/DdoPrimaryConstructionProduct"


@pytest.mark.gpu
@pytest.mark.provider_evidence
def test_actual_construction_binds_two_formal_configurations(
    commit_db_engine, native_settings, tmp_path
):
    scenario = PdfSourceScenario(
        section_content(
            (
                ("text", "A uses", "A uses", None),
                ("formula", "x + y", "x + y", "succeeded"),
                ("text", ".", ".", None),
            ),
            one_section=True,
        ),
        ("#/groups/0",),
        False,
    )
    with _registered_source(
        commit_db_engine, native_settings, tmp_path, "", scenario=scenario
    ) as source:
        kernel = admit_current_target(
            source, _recipe(tmp_path / "recipe", target="construction"), tmp_path / "consumer"
        )
        reports, selected = [], []
        formal_requests = set()
        for start in ("any_value", "relation"):
            request = current_consumer_request(source, kernel, (FORMAL,), discover=True)
            selections = {value.operation: value for value in request.selections}
            selections[FORMAL] = DemandOperationSelection(
                operation=FORMAL, parameters={"math_start": start}
            )
            request = request.model_copy(update={"selections": tuple(selections.values())})
            retained, _ = execute(kernel, request)
            with kernel.purpose("read").begin() as connection:
                page = read_demand_result(
                    connection, retained["demand_id"], project_id=PROJECT, limit=1000
                )
                (report,) = [
                    row
                    for row in page.members()
                    if row["kind_contract"] == kernel.identities[FORMAL_KIND, "kind"]
                    and row["member_id"] is None
                ]
                assert report["role"] == "result" and report["position"] == 0
                assert report["multiplicity"] == 1
                formal_requests.add(
                    next(
                        use["request_id"]
                        for use in page.record["uses"]
                        if use["use_id"] == report["use_id"]
                    )
                )
                reports.append(report)
                selected.append(SelectedSourceSetEntry.from_selected_header(report, page.cut))
        assert reports[0]["product_id"] != reports[1]["product_id"]
        assert len(formal_requests) == 2
        assert reports[0]["subject"] == reports[1]["subject"]
        assert reports[0]["analyzed_scope"] == reports[1]["analyzed_scope"]
        assert reports[0]["original_source"] == reports[1]["original_source"]
        shared_members = set.intersection(
            *({member["member_id"] for member in report["body"]["members"]} for report in reports)
        )
        assert shared_members
        request = current_consumer_request(source, kernel, (CONSTRUCTION,), discover=True)
        scopes = {
            **request.source_sets,
            **source_sets_record(
                (FrozenSourceSet.from_selected("construction-formal-evidence", tuple(selected)),)
            ),
        }
        request = request.model_copy(update={"source_sets": scopes})
        retained, _ = execute(kernel, request)
        with kernel.purpose("read").begin() as connection:
            page = read_demand_result(
                connection, retained["demand_id"], project_id=PROJECT, limit=1000
            )
            (construction,) = [
                row
                for row in page.members()
                if row["kind_contract"] == kernel.identities[CONSTRUCTION_KIND, "kind"]
                and row["member_id"] is None
            ]
            support_records = list(stream_selected_support(connection, page, whole_read=True))
            inputs = [
                item["record"]
                for item in support_records
                if item["relation"] == "ops.data_derivation_input"
                and item["record"]["derivation_id"] == construction["derivation_id"]
                and item["record"]["role"] == "formal"
            ]
        assert {
            row["product_id"]
            for row in page.members()
            if row["kind_contract"] == kernel.identities[FORMAL_KIND, "kind"]
            and row["member_id"] is None
        } <= {report["product_id"] for report in reports}
        formal_obligations = {
            row["obligation_id"]
            for row in page.record["obligations"]
            if row["operation_id"] == FORMAL
        }
        assert all(
            use["fate"] == "fulfilled"
            and {output["product_id"] for output in use["products"]}
            <= {report["product_id"] for report in reports}
            for use in page.record["uses"]
            if use["obligation_id"] in formal_obligations
        )
        assert {item["product_id"] for item in inputs} == {
            report["product_id"] for report in reports
        }
        assert len(inputs) == 2 and all(item["multiplicity"] == 1 for item in inputs)
        consumed_support = [
            row["record"]
            for row in support_records
            if row["relation"] == "ops.data_derivation_support"
            and row["record"]["derivation_id"] == construction["derivation_id"]
            and row["record"]["role"] == "formal"
        ]
        expected_origins = {
            report["product_id"]: (report["derivation_id"], report["use_id"]) for report in reports
        }
        assert {
            (row["support_derivation_id"], row["admission_use_id"]) for row in consumed_support
        } == set(expected_origins.values())
        # Unordered input ledger positions address the consumer's two reports.
        # Support positions retain each producer's original output position zero.
        emitted_products = {
            row["record"]["derivation_id"]: row["record"]["product_id"]
            for row in support_records
            if row["relation"] == "ops.data_derivation_output"
            and row["record"]["role"] == "result"
            and row["record"]["position"] == 0
            and row["record"]["member_id"] is None
            and row["record"]["derivation_id"] in {report["derivation_id"] for report in reports}
        }
        assert emitted_products == {
            report["derivation_id"]: report["product_id"] for report in reports
        }
        assert all(row["position"] == 0 for row in consumed_support)
        for item in inputs:
            assert {
                (row["support_derivation_id"], row["admission_use_id"])
                for row in consumed_support
                if emitted_products[row["support_derivation_id"]] == item["product_id"]
            } == {expected_origins[item["product_id"]]}
        targets = [item["target"] for item in construction["body"]["formal_support"]]
        by_occurrence = {str(item["position"]): item["product_id"] for item in inputs}
        assert set(by_occurrence) == {"0", "1"}
        report_members = {
            report["product_id"]: {member["member_id"] for member in report["body"]["members"]}
            for report in reports
        }
        citations = {product: set() for product in report_members}
        for target in targets:
            assert target["variant"] == "member" and target["role"] == "formal"
            product = by_occurrence[target["occurrence"]]
            assert target["member_id"] in report_members[product]
            citations[product].add(target["member_id"])
        assert all(citations.values())
        assert set.intersection(*citations.values()) & shared_members
        archive = tmp_path / "two-formal-reports"
        with kernel.purpose("read").begin() as connection:
            exported = export_demand_result(
                connection,
                retained["demand_id"],
                project_id=PROJECT,
                destination=archive,
                format="parquet",
                scope={"product_ids": [construction["product_id"]]},
            )
        with verified_demand_export(archive, manifest_digest=exported.manifest_digest) as (
            _,
            _,
            _,
            index,
        ):
            detached = index.mapping("kb.data_product", ("id",))
            assert {report["product_id"] for report in reports} <= set(detached)
            detached_inputs = [
                row
                for row in index.rows("ops.data_derivation_input")
                if row["derivation_id"] == construction["derivation_id"] and row["role"] == "formal"
            ]
            assert {row["product_id"] for row in detached_inputs} == {
                report["product_id"] for report in reports
            }
            assert {
                (row["support_derivation_id"], row["admission_use_id"])
                for row in index.rows("ops.data_derivation_support")
                if row["derivation_id"] == construction["derivation_id"] and row["role"] == "formal"
            } == set(expected_origins.values())
        empty_scopes = {
            **request.source_sets,
            **source_sets_record(
                (FrozenSourceSet.from_selected("construction-formal-evidence", ()),)
            ),
        }
        empty_request = request.model_copy(update={"source_sets": empty_scopes})
        empty_retained, _ = execute(kernel, empty_request)
        with kernel.purpose("read").begin() as connection:
            empty = read_demand_result(
                connection, empty_retained["demand_id"], project_id=PROJECT, limit=1000
            )
        assert not any(
            row["kind_contract"] == kernel.identities[CONSTRUCTION_KIND, "kind"]
            for row in empty.members()
        )
