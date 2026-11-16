"""Real current PDF transport with independently specified finite recognition data."""

from hashlib import sha256

import pytest
from sqlalchemy import text

from corpus_structure.semantic.pdf_record_reader import published_record_reader
from corpus_structure.semantic.pdf_storage import (
    NativeDocumentUnavailable,
    read_pdf_artifact,
    read_pdf_manifest,
    read_pdf_product,
    trace_pdf_occurrence,
)
from semantic.current_pdf_integration_support import RICH_RESPONSE, current_integration_journey
from semantic.pdf_native_source_support import IMAGE


def selected_reference(case, operation, snapshot=None):
    from corpus_structure.serve.selected_pdf import SelectedPdfSourceReference

    snapshot = case.snapshot if snapshot is None else snapshot
    obligations = {row["obligation_id"]: row for row in snapshot["obligations"]}
    use = next(
        row
        for row in snapshot["uses"]
        if row["fate"] == "fulfilled"
        and obligations[row["obligation_id"]]["operation_id"] == operation
    )
    output = next(row for row in use["products"] if row["role"] == "result")
    return SelectedPdfSourceReference(
        project_id=case.original.project_id,
        demand_id=snapshot["demand_id"],
        read_id=snapshot["read_id"],
        use_id=use["use_id"],
        product_id=output["product_id"],
        derivation_id=use["derivation_id"],
    )


def test_current_observation_reclaim_preserves_first_publication_without_fresh_provider_credit(
    scenario_seeds,
    tmp_path,
    monkeypatch,
    native_settings,
):
    with current_integration_journey(
        scenario_seeds, tmp_path, monkeypatch, native_settings, reclaim_after_recognition=True
    ) as case:
        assert case.interruption is not None and case.reclaimed_fence is not None
        receipt = case.observation_source.receipt
        assert receipt.attempt > case.reclaimed_fence["attempt"] > 1
        assert case.calls == ["capture", "recognize", "recognition-adopt"]
        assert len(case.observations) == 4
        assert len({reference for reference, _ in case.observations}) == 2
        assert (
            case.values["source.pdf_recognition/observe"]["result"]["pages"][0]["outcome"]
            == "succeeded"
        )
        assert receipt.pages[0].adapter_reused is True
        with case.clone.admin.connect() as connection:
            for reference in receipt.pages[0].observations:
                origin = reference.publication_context
                assert origin.attempt == 1 and origin.attempt < receipt.attempt
                assert origin.holder != receipt.holder
                retained = connection.scalar(
                    text(
                        "SELECT publication_context FROM ops.pdf_product WHERE task_id=:task AND product_key=:key"
                    ),
                    {"task": reference.task_id, "key": reference.product_key},
                )
                assert retained == origin.model_dump(mode="json")
        assert "integrated" in case.publications


def test_current_observation_reads_refuse_wrong_kind_tuple_custody_and_revoked_support(
    scenario_seeds,
    tmp_path,
    monkeypatch,
    native_settings,
):
    from copy import deepcopy
    from typing import cast

    from sqlalchemy.exc import DBAPIError

    from corpus_structure.semantic._data_operation_wire import WireRevokeDataSupportRequest
    from corpus_structure.semantic.data_operation_json import json_bytes
    from corpus_structure.semantic.data_operation_storage import DataOperationStorage
    from corpus_structure.serve.selected_pdf import (
        acquire_selected_pdf_observations,
        acquire_selected_pdf_source,
    )

    with current_integration_journey(
        scenario_seeds, tmp_path, monkeypatch, native_settings
    ) as case:
        observed = case.observation_source.reference
        raw = selected_reference(case, "source.pdf/capture")
        assert observed != raw
        with case.reader().begin() as connection:
            assert (
                acquire_selected_pdf_observations(connection, observed).receipt
                == case.observation_source.receipt
            )
            for reader, reference in (
                (acquire_selected_pdf_source, observed),
                (acquire_selected_pdf_observations, raw),
                (
                    acquire_selected_pdf_observations,
                    observed.model_copy(update={"product_id": raw.product_id}),
                ),
                (
                    acquire_selected_pdf_observations,
                    observed.model_copy(update={"project_id": observed.project_id + ":foreign"}),
                ),
            ):
                with pytest.raises(DBAPIError), connection.begin_nested():
                    reader(connection, reference)
        receipt = case.observation_source.receipt
        for mutation in ("source", "recipe", "report", "origin", "request"):
            forged = deepcopy(receipt.model_dump(mode="json"))
            if mutation == "source":
                forged["source_digest"] = "f" * 64
            elif mutation == "recipe":
                forged["pages"][0]["recipe_digest"] = "f" * 64
            elif mutation == "report":
                forged["pages"][0]["report_digest"] = "f" * 64
            elif mutation == "origin":
                forged["pages"][0]["observations"][0]["publication_context"]["attempt"] += 1
            else:
                forged["request_id"] += ":foreign"
            with (
                case.kernel.purpose("write").begin() as connection,
                pytest.raises(DBAPIError),
                connection.begin_nested(),
            ):
                connection.scalar(
                    text(
                        "SELECT ops.pdf_observation_projection(CAST(:receipt AS jsonb),:task,:attempt,:holder)"
                    ),
                    {
                        "receipt": json_bytes(forged).decode(),
                        "task": receipt.task_id,
                        "attempt": receipt.attempt,
                        "holder": receipt.holder,
                    },
                )
        with case.kernel.purpose("write").begin() as connection:
            DataOperationStorage(connection).revoke_data_support(
                cast(
                    WireRevokeDataSupportRequest,
                    dict(
                        project_id=case.original.project_id,
                        original_source=case.original.document_key,
                        selector_kind="product",
                        selector=observed.product_id,
                        reason="independent observation-set support withdrawal",
                    ),
                )
            )
        with (
            case.reader().begin() as connection,
            pytest.raises(DBAPIError),
            connection.begin_nested(),
        ):
            acquire_selected_pdf_observations(connection, observed)
        # Revocation withdraws standing rather than erasing the actual raw attempts.
        with case.clone.admin.connect() as connection:
            assert (
                connection.scalar(
                    text(
                        "SELECT count(*) FROM ops.pdf_product WHERE task_id=:task AND kind='recognition_observation'"
                    ),
                    {"task": receipt.task_id},
                )
                == 2
            )


def test_current_policy_only_change_reuses_native_observation_support_without_provider_rerun(
    scenario_seeds,
    tmp_path,
    monkeypatch,
    native_settings,
):
    from corpus_structure.core.method import MethodSettings
    from corpus_structure.orchestrate.source_operation import run_source_operation
    from corpus_structure.orchestrate.source_request import SourceRunRequest, WholeDocument
    from corpus_structure.semantic.data_operation_service import read_data_demand
    from corpus_structure.semantic.runtime import open_runtime_engine
    from corpus_structure.serve.selected_pdf import (
        acquire_selected_pdf_observations,
        acquire_selected_pdf_source,
    )
    from semantic.current_pdf_integration_support import ROOT, current_pdf_recipe
    from semantic.current_pdf_source_support import admit_current_target

    with current_integration_journey(
        scenario_seeds, tmp_path, monkeypatch, native_settings
    ) as case:
        before = tuple(case.calls)
        first_publication = case.publications["integrated"]
        policy = dict(
            policy_id="pdf-integration-v1",
            conflict_action="keep",
            unmatched_action="add",
            specialized_crop_precedence=True,
            comparison_demand="lexical",
        )
        next_kernel = admit_current_target(
            case,
            current_pdf_recipe(tmp_path, integration_policy=policy),
            tmp_path / "policy-consumer",
        )
        assert next_kernel.prepared.release_id != case.prepared.release_id
        request = SourceRunRequest(
            project_id=case.original.project_id,
            release_id=next_kernel.prepared.release_id,
            runtime_id=next_kernel.runtime,
            domain="toy",
            workflow="capture",
            selection=WholeDocument(),
            documents=(case.original.document_key,),
            pdf_mode="integrated",
            recognition_pages=(1,),
            targets=("source.pdf_integrated_views/discovery",),
        )
        with open_runtime_engine(
            case.settings, "current-policy-remap", purpose="write", max_size=6
        ) as engine:
            result = run_source_operation(
                engine,
                request,
                MethodSettings(data_dir=tmp_path, model_cache=tmp_path),
                source_root=ROOT,
                admission_engine=next_kernel.purpose("admit"),
            )
        assert tuple(case.calls) == before
        with case.reader().begin() as connection:
            snapshot = read_data_demand(connection, result.demand_id, view="products")
            reused = acquire_selected_pdf_observations(
                connection, selected_reference(case, "source.pdf_recognition/observe", snapshot)
            )
            assert reused.reference.product_id == case.observation_source.reference.product_id
            assert reused.reference.derivation_id == case.observation_source.reference.derivation_id
            assert reused.receipt == case.observation_source.receipt
            remapped = acquire_selected_pdf_source(
                connection, selected_reference(case, "source.pdf_integrated/reconcile", snapshot)
            )
            assert remapped.physical.task_id != first_publication.task_id
            assert (
                remapped.receipt.publication.recipe_digest
                != case.values["source.pdf_integrated/reconcile"]["result"]["recipe_digest"]
            )
            reader = published_record_reader(
                connection, remapped.physical, projection_context=next_kernel.prepared
            )
            assert reader is not None
            decisions = list(reader.iter_companions("relation"))
            assert decisions and any(
                row.get("outcome") == "retained_alternative" for row in decisions
            )


def test_current_rich_integration_retains_separate_claims_inventory_and_originals(
    scenario_seeds, tmp_path, monkeypatch, native_settings
):
    # Trailing provider whitespace is still retained verbatim, across byte pages.
    raw = RICH_RESPONSE + b"\n" * 70000
    with current_integration_journey(
        scenario_seeds,
        tmp_path,
        monkeypatch,
        native_settings,
        raw_responses=(raw, raw),
    ) as case:
        assert "source.pdf_integrated/reconcile" in case.values
        selected = case.publications["integrated"]
        organized = case.publications["organized"]
        assert selected.task_id != organized.task_id
        assert len(case.observations) == 2
        assert all(
            reference.task_id != selected.task_id and reference.task_id != organized.task_id
            for reference, _ in case.observations
        )
        assert len({reference.task_id for reference, _ in case.observations}) == 1
        retained_effect = case.observation_source.receipt
        assert retained_effect.task_id == case.observations[0][0].task_id
        assert len(retained_effect.pages) == 1 and len(retained_effect.pages[0].observations) == 2
        for request in retained_effect.pages[0].observations:
            assert request.publication_context.task_id == retained_effect.task_id
            assert request.publication_context.attempt == retained_effect.attempt
            assert request.publication_context.runtime_id == retained_effect.runtime_id
        assert case.calls == ["capture", "recognize"]
        with case.reader().connect() as connection:
            reader = published_record_reader(connection, selected, projection_context=case.prepared)
            assert reader is not None
            descriptor = reader.product_descriptor()
            assert descriptor["kind"] == "integrated"
            assert descriptor["revision"]["release_id"] == case.prepared.release_id
            occurrences = list(reader.iter_companions("occurrence"))
            cells = [row for row in occurrences if row["kind"] == "cell"]
            assert cells
            assert any("/meta/tabular_chart/" in row["occurrence_id"] for row in cells)
            assert any(row.get("text") == "y+2" and row["kind"] == "formula" for row in occurrences)
            for reference, _observed in case.observations:
                retained = read_pdf_product(connection, **reference.values(), include_body=True)
                assert (
                    retained["body"]["observation"]["raw_response_digest"]
                    == sha256(raw).hexdigest()
                )
                assert (
                    retained["body"]["observation"]["image"]["artifact_digest"]
                    == sha256(IMAGE).hexdigest()
                )
                assert retained["body"]["inputs"] == [
                    {**case.publications["native"].values(), "role": "structural"}
                ]
            chart = next(row for row in cells if "/meta/tabular_chart/" in row["occurrence_id"])
            trace = trace_pdf_occurrence(
                connection, **selected.values(), occurrence_id=chart["occurrence_id"]
            )
            assert trace["complete"] is True
            assert any(
                node["product_key"] == case.observations[0][0].product_key
                for node in trace["nodes"]
            )
            assert all(
                node["artifact_digest"] == case.original.content_hash for node in trace["nodes"]
            )
            with pytest.raises(ValueError, match="exceeds requested row budget"):
                trace_pdf_occurrence(
                    connection, **selected.values(), occurrence_id=chart["occurrence_id"], limit=1
                )
            scoped = read_pdf_product(
                connection, **selected.values(), occurrence_id=chart["occurrence_id"]
            )
            assert "body" not in scoped and "content" not in scoped["descriptor"]
            assert [row["occurrence_id"] for row in scoped["occurrences"]] == [
                chart["occurrence_id"]
            ]
            assert all(
                row["body"]["scope"] in {"whole_document", "page:1"} for row in scoped["coverage"]
            )
            # Page the actual manifest independently of the scoped companion read.
            coverage, after = [], ""
            while True:
                page = read_pdf_manifest(
                    connection, **selected.values(), collection="coverage", after=after, limit=1
                )
                coverage.extend(page["rows"])
                if page["cursor"] is None:
                    break
                after = page["cursor"]
            assert {row["coverage_id"] for row in coverage} == {
                row["coverage_id"] for row in case.drafts["integrated"].companions["coverage"]
            }
            parts, offset = [], 0
            while True:
                page = read_pdf_artifact(
                    connection,
                    **selected.values(),
                    artifact_digest=sha256(raw).hexdigest(),
                    offset=offset,
                )
                assert len(page["content"]) <= 65536 and page["total_bytes"] == len(raw)
                parts.append(page["content"])
                if page["next_offset"] is None:
                    break
                offset = page["next_offset"]
            assert len(parts) > 1 and b"".join(parts) == raw
            assert (
                read_pdf_artifact(
                    connection, **selected.values(), artifact_digest=sha256(IMAGE).hexdigest()
                )["content"]
                == IMAGE
            )
            with pytest.raises(NativeDocumentUnavailable, match="custody"):
                read_pdf_artifact(connection, **selected.values(), artifact_digest="0" * 64)
            with pytest.raises(ValueError, match="byte length"):
                read_pdf_artifact(
                    connection,
                    **selected.values(),
                    artifact_digest=sha256(raw).hexdigest(),
                    offset=len(raw) + 1,
                )
            with pytest.raises(NativeDocumentUnavailable):
                read_pdf_product(
                    connection,
                    task_id=selected.task_id,
                    product_key=selected.product_key,
                    content_digest="0" * 64,
                )


def test_current_failed_later_request_keeps_prior_observation_without_completed_product(
    scenario_seeds, tmp_path, monkeypatch, native_settings
):
    with current_integration_journey(
        scenario_seeds,
        tmp_path,
        monkeypatch,
        native_settings,
        raw_responses=(RICH_RESPONSE, None),
        outcome="failed",
        expect_unresolved_page=True,
    ) as case:
        assert case.failure is not None
        assert "integrated" not in case.publications
        assert "source.pdf_integrated/reconcile" not in case.values
        observed_set = case.values["source.pdf_recognition/observe"]["result"]
        assert observed_set["pages"][0]["outcome"] == "failed"
        assert [reading["outcome"] for reading in observed_set["pages"][0]["observations"]] == [
            "succeeded",
            "failed",
        ]
        assert len(case.observations) == 2
        first, later = case.observations
        assert first[0].task_id == later[0].task_id
        assert first[0].task_id != case.publications["organized"].task_id
        with case.reader().connect() as connection:
            succeeded = read_pdf_product(connection, **first[0].values(), include_body=True)
            failed = read_pdf_product(connection, **later[0].values(), include_body=True)
            assert succeeded["body"]["observation"]["outcome"] == "succeeded"
            assert (
                succeeded["body"]["observation"]["raw_response_digest"]
                == sha256(RICH_RESPONSE).hexdigest()
            )
            assert succeeded["occurrences"]
            assert failed["body"]["observation"]["outcome"] == "failed"
            assert "raw_response_digest" not in failed["body"]["observation"]
            assert failed["occurrences"] == []
            assert failed["coverage"] and all(
                row["body"]["outcome"] == "unknown" for row in failed["coverage"]
            )
            assert (
                failed["body"]["observation"]["diagnostic"]
                == "controlled connection closed before response"
            )
            assert all(row["body"]["outcome"] != "complete" for row in succeeded["coverage"])
        with case.clone.admin.connect() as connection:
            assert (
                connection.scalar(
                    text(
                        "SELECT count(DISTINCT publication.build_id) FROM ops.pdf_published_revision publication "
                        "JOIN ops.task task ON task.id=publication.task_id "
                        "JOIN ops.data_request request ON request.id=task.data_request_id "
                        "JOIN ops.demand_use use_ ON use_.request_id=request.id "
                        "WHERE use_.demand_id=:demand AND request.operation_id='source.pdf_integrated/reconcile'"
                    ),
                    {"demand": case.demand_id},
                )
                == 0
            )
