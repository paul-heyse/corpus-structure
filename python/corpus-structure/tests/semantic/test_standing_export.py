"""Detached exports retain independent standing and bounded detail references."""

import json

import pyarrow as pa
import pyarrow.parquet as pq
import pytest

from corpus_structure.semantic.analytics import CapturedPacket, compile_projection
from corpus_structure.semantic.contracts import execution_payload
from corpus_structure.semantic.query import SnapshotBinding
from corpus_structure.serve.export import export_packet


def packet():
    from .test_analytics import prepared_inputs

    prepared = prepared_inputs()[2]
    binding = SnapshotBinding(prepared.release_id, "z", 1, "capture:test")
    projection = compile_projection(prepared, binding)
    rows = {
        "fact": [
            dict(
                fact_id=k,
                subject_id="subject",
                property_id="property",
                object_value_id="value",
                qualification_value_id=None,
                qualification_key="",
            )
            for k in ("a", "b")
        ],
        "selection": [dict(fact_id="a")],
        "assessment": [
            dict(
                fact_id="a",
                assessment_id=f"assessment:{i:02}",
                operation_id="comparison",
                operation_version="1",
                outcome="accepted" if i % 2 else "rejected",
            )
            for i in range(10)
        ],
        "occurrence": [
            dict(
                occurrence_id="o",
                fact_id="a",
                source="source",
                item="item",
                batch_id="batch",
                report_object_value_id="value",
                report_qualification_value_id=None,
            )
        ],
        "occurrence_establishment": [dict(occurrence_id="o", establishment="stated")],
    }
    relations = {
        p.name: pa.Table.from_pylist(
            [
                dict(release_id=binding.release_id, realization_id=binding.realization_id, **row)
                for row in rows.get(p.name, [])
            ],
            schema=p.schema,
        )
        for p in projection.relations
    }
    return CapturedPacket(
        binding,
        projection.projection_id,
        projection.profile.digest,
        relations,
        execution_model_id=prepared.execution_model_id,
        execution_contract=execution_payload(prepared),
    )


@pytest.mark.parametrize("format", ["jsonl", "parquet"])
def test_standing_export_keeps_selection_assessment_establishment_independent(tmp_path, format):
    captured = packet()
    manifest = export_packet(captured, tmp_path / format, format=format)
    assert manifest["format"] == "semantic-export-4"
    detail = manifest["relations"]["fact_standing_v2"]
    path = tmp_path / format / detail["file"]
    rows = (
        pq.read_table(path).to_pylist()
        if format == "parquet"
        else [json.loads(line) for line in path.read_text().splitlines()]
    )
    assert [r["fact_id"] for r in rows] == ["a", "b"]
    selected, other = rows
    assert selected["selection"] == "selected"
    assert selected["assessments"]["count"] == 10
    assert selected["assessments"]["population_complete"] is False
    assert [r["assessment_id"] for r in selected["assessments"]["references"]] == [
        f"assessment:{i:02}" for i in range(8)
    ]
    assert {r["outcome"] for r in selected["assessments"]["references"]} == {"accepted", "rejected"}
    assert selected["establishments"]["references"] == [
        dict(reference_id="o", kind="stated", collection="supports")
    ]
    assert other["selection"] == "not_selected"
    assert other["assessments"]["availability"] == "unassessed"
    assert other["establishments"]["availability"] == "unavailable"
    assert "payload" not in path.read_text() if format == "jsonl" else True
