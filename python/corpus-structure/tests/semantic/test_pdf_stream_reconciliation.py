"""Private disk-backed selection: independent source/companion and replay expectations."""

import json

import pytest
from docling_core.types.doc import DoclingDocument

from corpus_structure.ingest.pdf_stream_reconciliation import (
    ReconciliationJournal,
    reconcile_pdf_stream,
)

from . import test_pdf_integrated as integration_fixtures
from .test_pdf_integrated import pin
from .test_pdf_reconciliation import recognized

native_source = integration_fixtures.native_source


def test_phase_partition_is_stable_and_retains_exact_binary(tmp_path):
    journal = ReconciliationJournal(tmp_path / "journal")
    rows = journal.collection("mapped_inputs")
    for i, role in enumerate(("C", "A", "C", "B")):
        rows.append((i, {"observation": {"pass_role": role}}, bytes([0, i, 255])))
    rows.sort(key=lambda row: row[1]["observation"]["pass_role"] == "C")
    assert [(row[0], row[2]) for row in rows] == [
        (1, b"\0\1\xff"),
        (3, b"\0\3\xff"),
        (0, b"\0\0\xff"),
        (2, b"\0\2\xff"),
    ]
    assert list(journal.directory.glob("*.arrow"))
    with pytest.raises(ValueError, match="already being read"):
        rows.append((4, {"observation": {"pass_role": "A"}}, b"x"))
    journal.close()
    with pytest.raises(FileExistsError):
        ReconciliationJournal(tmp_path / "journal")


def test_candidate_journal_preserves_exact_ipc_without_json_interior_or_codec_roundtrip(
    tmp_path, monkeypatch
):
    import pyarrow as pa

    from corpus_structure.semantic.pdf_payloads import (
        EncodedPagePayload,
        PreparedPayloadFamily,
        prepare_payload_family,
    )

    family = prepare_payload_family()
    page = {
        "page_no": 7,
        "has_words": True,
        "has_chars": False,
        "candidates": [
            dict(
                page_no=7,
                text="opaque-candidate",
                left=1,
                top=-0.0,
                right=3.5,
                bottom=4,
                origin="TOPLEFT",
                basis="source",
                ocr_region_index=2,
            )
        ],
    }
    encoded = EncodedPagePayload(
        family.encode(page), family.schema_digest, family.logical_digest(page), 7
    )

    def refuse(*args, **kwargs):
        raise AssertionError("journal must not encode/decode the candidate interior")

    monkeypatch.setattr(PreparedPayloadFamily, "encode", refuse)
    monkeypatch.setattr(PreparedPayloadFamily, "decode", refuse)
    journal = ReconciliationJournal(tmp_path / "journal")
    rows = journal.collection("native_metadata")
    rows.append({"kind": "inline_candidate_pages", "ordinal": 3, "value": encoded})
    expected = [{"kind": "inline_candidate_pages", "ordinal": 3, "value": encoded}]
    assert list(rows) == list(rows) == expected
    with pa.memory_map(str(rows.paths[0]), "r") as source:
        batch = pa.ipc.open_file(source).get_batch(0)
        assert batch.column("raw")[0].as_py() == encoded.content
        body = batch.column("body")[0].as_py()
        assert "opaque-candidate" not in body and "candidates" not in body
        assert json.loads(body)["value"]["logical_digest"] == encoded.logical_digest
    journal.close()
    with pytest.raises(TypeError, match="encoded Arrow payload"):
        ReconciliationJournal(tmp_path / "invalid").collection("native_metadata").append(
            {"kind": "inline_candidate_pages", "ordinal": 0, "value": page}
        )


def test_native_stream_never_uses_legacy_publication_envelope(native_source, tmp_path, monkeypatch):
    from corpus_structure.ingest import pdf, pdf_hierarchy

    def refuse(*args, **kwargs):
        raise AssertionError("whole native snapshot/publication must not be created")

    document = DoclingDocument.model_validate(native_source.payload["document"])
    monkeypatch.setattr(pdf, "publication_payload", refuse)
    monkeypatch.setattr(pdf_hierarchy, "snapshot", refuse)
    result = reconcile_pdf_stream(
        document,
        pin(1, "native", "0" * 64, "structural"),
        iter(()),
        native_source.payload["artifact_digest"],
        directory=tmp_path,
    )
    with result:
        assert result.document is document
        rows = list(result.iter_companions())
        occurrences = [row for family, row in rows if family == "occurrence"]
        assert {row["occurrence_id"] for row in occurrences} == {
            "#/body",
            "#/furniture",
            "#/texts/0",
            "#/texts/1",
            "#/tables/0",
            "#/tables/0/data/table_cells/0",
            "#/tables/0/data/table_cells/1",
        }
        decisions = [row for family, row in rows if family == "relation"]
        assert len(decisions) == 7
        assert all(row["outcome"] == "selected" for row in decisions)
        assert [row for family, row in rows if family == "coverage"] == [
            {
                "coverage_id": "selection",
                "scope": "whole_document",
                "family": "selected_content",
                "discovery_policy": "pdf-integration-v1",
                "outcome": "unknown",
                "detail": "No qualified recognition coverage",
            }
        ]
        assert list(result.iter_companions()) == rows
    with pytest.raises(ValueError, match="closed"):
        list(result.iter_companions())


def test_stream_retains_unmatched_observation_and_mapping_coverage(native_source, tmp_path):
    raw = b"<x_0.1><y_0.7>novel text<x_0.7><y_0.8><class_Text>"
    obs = recognized(native_source, raw)
    document = DoclingDocument.model_validate(native_source.payload["document"])
    with reconcile_pdf_stream(
        document,
        pin(1, "native", "0" * 64, "structural"),
        iter([(pin(2, "a", "1" * 64, "recognition"), obs, raw)]),
        native_source.payload["artifact_digest"],
        directory=tmp_path,
    ) as result:
        rows = list(result.iter_companions())
        assert any(
            family == "occurrence" and row.get("text") == "novel text" for family, row in rows
        )
        assert any(family == "relation" and row["outcome"] == "added" for family, row in rows)
        assert len([row for family, row in rows if family == "input"]) == 2
        assert any(family == "coverage" and row["outcome"] == "partial" for family, row in rows)
        # Named Arrow replay preserves companion values without a full product envelope.
        assert all(json.dumps(row, allow_nan=False) for _, row in rows)


def test_recognition_replay_has_delivery_independent_pin_order_and_refuses_duplicates(tmp_path):
    from corpus_structure.ingest.pdf_stream_reconciliation import (
        iter_recognition_replay,
        write_recognition_replay,
    )

    observations = [
        ({"product_key": "b", "task_id": 2}, {"label": "B"}, b"\0B\xff"),
        ({"task_id": 1, "product_key": "a"}, {"label": "A"}, b"A"),
    ]
    expected = [observations[1], observations[0]]
    for i, rows in enumerate((observations, list(reversed(observations)))):
        path = tmp_path / f"input-{i}.arrow"
        write_recognition_replay(path, iter(rows))
        assert list(iter_recognition_replay(path)) == expected
    duplicate = tmp_path / "duplicate.arrow"
    write_recognition_replay(duplicate, [observations[0], observations[0]])
    with pytest.raises(ValueError, match="duplicate qualified"):
        list(iter_recognition_replay(duplicate))


def test_companions_are_exact_part_streams_in_model_owned_profile(native_source, tmp_path):
    from hashlib import sha256

    import pyarrow as pa

    from corpus_structure.ingest.pdf_stream_reconciliation import write_companion_artifacts
    from corpus_structure.semantic.pdf_staging import companion_profile

    document = DoclingDocument.model_validate(native_source.payload["document"])
    with reconcile_pdf_stream(
        document,
        pin(1, "native", "0" * 64, "structural"),
        iter(()),
        native_source.payload["artifact_digest"],
        directory=tmp_path,
    ) as result:
        admitted = []
        files = write_companion_artifacts(
            result, tmp_path / "companions", build_id="build", on_batch=admitted.append
        )
        assert list(files) == admitted
        rows = []
        for replay in files:
            replay.verify()
            with pa.memory_map(str(replay.path), "r") as source:
                reader = pa.ipc.open_file(source)
                for number in range(reader.num_record_batches):
                    rows.extend(
                        (replay.family, row) for row in reader.get_batch(number).to_pylist()
                    )
        for family in ("input", "occurrence", "relation", "mapping_report", "coverage", "health"):
            stream_id = "companion:" + family
            parts = [
                row
                for kind, row in rows
                if kind == "artifact_part" and row["stream_id"] == stream_id
            ]
            data = b"".join(row["body"] for row in sorted(parts, key=lambda row: row["ordinal"]))
            manifest = next(
                row
                for kind, row in rows
                if kind == "artifact_stream" and row["stream_id"] == stream_id
            )
            assert manifest["byte_length"] == len(data)
            assert manifest["serialization_sha256"] == sha256(data).hexdigest()
            assert manifest["encoding_profile"] == companion_profile(family)
            assert all(row["product_id"] == "build" for row in parts)
            if family == "occurrence":
                assert len(data.splitlines()) == 7
            if family == "health":
                assert json.loads(data)["source_fidelity"] == "unassessed"


@pytest.mark.parametrize(
    ("reading", "bottom", "outcome", "structural_ids", "output_ids"),
    [
        ("corrected", "0.066666", "matched", {"#/texts/0"}, {"#/texts/1"}),
        ("equal", "0.066666", "matched", {"#/texts/0"}, {"#/texts/0"}),
        (
            "corrected",
            "0.166666",
            "ambiguous",
            {"#/texts/0", "#/texts/1"},
            {"#/texts/0", "#/texts/1"},
        ),
    ],
)
def test_streamed_correspondence_pairs_keep_qualified_output_endpoints(
    native_source, tmp_path, reading, bottom, outcome, structural_ids, output_ids
):
    from corpus_structure.ingest.pdf_reconciliation import select_pdf_integration

    raw = f"<x_0.05><y_0.033333>{reading}<x_0.3><y_{bottom}><class_Text>".encode()
    observations = [(pin(2, "a", "1" * 64, "recognition"), recognized(native_source, raw), raw)]
    structural = pin(1, "native", "0" * 64, "structural")
    expected = select_pdf_integration(
        native_source.payload,
        structural,
        observations,
        native_source.original,
        native_source.recipe,
        native_source.schema,
    ).values()
    with reconcile_pdf_stream(
        DoclingDocument.model_validate(native_source.payload["document"]),
        structural,
        iter(observations),
        native_source.payload["artifact_digest"],
        directory=tmp_path,
    ) as result:
        rows = list(result.iter_companions())
        relations = [row for family, row in rows if family == "relation"]
        assert relations == expected["relations"]
        correspondence = next(row for row in relations if row["kind"] == "correspondence")
        assert correspondence["outcome"] == outcome
        assert {
            endpoint["occurrence_id"]
            for endpoint in correspondence["endpoints"]
            if endpoint["role"] == "input" and endpoint["input_index"] == 0
        } == structural_ids
        assert {
            endpoint["occurrence_id"]
            for endpoint in correspondence["endpoints"]
            if endpoint["role"] == "output"
        } == output_ids
        assert {"role": "input", "input_index": 1, "occurrence_id": "block-0"} in correspondence[
            "endpoints"
        ]


def test_correspondence_evidence_is_owned_before_later_equal_reading(native_source, tmp_path):
    from corpus_structure.ingest.pdf_reconciliation import select_pdf_integration

    raw = b"<x_0.05><y_0.033333>corrected<x_0.3><y_0.066666><class_Text>"
    observations = [
        (pin(task, "a", str(task) * 64, "recognition"), recognized(native_source, raw), raw)
        for task in (2, 3)
    ]
    structural = pin(1, "native", "0" * 64, "structural")
    expected = select_pdf_integration(
        native_source.payload,
        structural,
        observations,
        native_source.original,
        native_source.recipe,
        native_source.schema,
    ).values()
    with reconcile_pdf_stream(
        DoclingDocument.model_validate(native_source.payload["document"]),
        structural,
        iter(observations),
        native_source.payload["artifact_digest"],
        directory=tmp_path,
    ) as result:
        relations = [row for family, row in result.iter_companions() if family == "relation"]
        assert relations == expected["relations"]
        correspondences = [row for row in relations if row["kind"] == "correspondence"]
        assert len(correspondences) == 2
        for row, source_index, source_id, equal in zip(
            correspondences, (0, 1), ("#/texts/0", "block-0"), (False, True), strict=True
        ):
            evidence = json.loads(row["evidence"])
            assert evidence["candidates"][0][:2] == [source_index, source_id]
            assert evidence["comparison"]["text_equal"] is equal
            assert {"role": "output", "occurrence_id": "#/texts/1"} in row["endpoints"]
