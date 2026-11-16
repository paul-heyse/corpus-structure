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
        assert all(reference.task_id != selected.task_id and reference.task_id != organized.task_id for reference, _ in case.observations)
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
                assert retained["body"]["observation"]["raw_response_digest"] == sha256(raw).hexdigest()
                assert retained["body"]["observation"]["image"]["artifact_digest"] == sha256(IMAGE).hexdigest()
                assert retained["body"]["inputs"] == [{**case.publications["native"].values(), "role": "structural"}]
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
        assert [reading["outcome"] for reading in observed_set["pages"][0]["observations"]] == ["succeeded", "failed"]
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
            assert connection.scalar(text(
                "SELECT count(DISTINCT publication.build_id) FROM ops.pdf_published_revision publication "
                "JOIN ops.task task ON task.id=publication.task_id "
                "JOIN ops.data_request request ON request.id=task.data_request_id "
                "JOIN ops.demand_use use_ ON use_.request_id=request.id "
                "WHERE use_.demand_id=:demand AND request.operation_id='source.pdf_integrated/reconcile'"
            ), {"demand": case.demand_id}) == 0
