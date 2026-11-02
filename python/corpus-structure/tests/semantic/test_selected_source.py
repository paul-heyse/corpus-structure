"""Independent selected membership, offline preparation and incomplete-package refusals."""

import base64
import json
from dataclasses import replace
from hashlib import sha256
from pathlib import Path

import pytest

from corpus_structure.semantic.analysis_contracts import prepare_interpretation_context
from corpus_structure.semantic.pdf_record_reader import PublishedPdfReader
from corpus_structure.serve.companion_export import PublishedSourcePin
from corpus_structure.serve.selected_source import (
    AdditionalContextRequired,
    SelectedSourceExportRequest,
    SelectedSourceReader,
    SelectedSourceSelection,
    SelectedSourceUnavailable,
    _write_selected_package,
)


class SourceBytes(PublishedPdfReader):
    def __init__(self):
        self.revision = {
            "release_id": "source-production-release",
            "source_digest": "a" * 64,
            "schema_digest": "b" * 64,
            "recipe_digest": "c" * 64,
        }


def independent_records(large=False):
    return [
        dict(
            pointer="#/groups/8",
            ordinal=8,
            parent_pointer="#/body",
            label="section",
            body={
                "self_ref": "#/groups/8",
                "name": "Selected",
                "children": [
                    {"$ref": "#/texts/42"},
                    {"$ref": "#/tables/2"},
                    {"$ref": "#/texts/43"},
                ],
            },
        ),
        dict(
            pointer="#/texts/42",
            ordinal=9,
            parent_pointer="#/groups/8",
            label="formula",
            body={
                "self_ref": "#/texts/42",
                "label": "formula",
                "orig": "original A",
                "text": "x=1",
                "caption": "😀" * 30000 if large else "\u03b1",
            },
        ),
        dict(
            pointer="#/tables/2",
            ordinal=10,
            parent_pointer="#/groups/8",
            label="table",
            body={
                "self_ref": "#/tables/2",
                "data": {
                    "table_cells": [
                        {"text": "cell", "start_row_offset_idx": 0, "start_col_offset_idx": 0}
                    ]
                },
            },
        ),
        dict(
            pointer="#/texts/43",
            ordinal=11,
            parent_pointer="#/groups/8",
            label="formula",
            body={
                "self_ref": "#/texts/43",
                "label": "formula",
                "orig": "original B",
                "text": "x=1",
            },
        ),
    ]


def source_events(records, outcome="succeeded"):
    membership = "".join(
        f"{r['pointer']}\t{r['ordinal']}\t{r['parent_pointer']}\n" for r in records
    ).encode()
    yield dict(
        event="selection_metadata",
        selected_count=len(records),
        membership_sha256=sha256(membership).hexdigest(),
    )
    for record in records:
        yield dict(
            event="record_start",
            record_id="record:" + record["pointer"],
            role="selected",
            section_pointer="#/groups/8",
            **{k: v for k, v in record.items() if k != "body"},
        )
        yield dict(
            event="native_fragment",
            native=dict(
                kind="literal", value=json.dumps(record["body"], ensure_ascii=False), prefix=""
            ),
        )
        yield dict(event="record_end", pointer=record["pointer"])
    yield dict(event="context", kind="ancestor", pointer="#/body", label="document", ordinal=0)
    yield dict(
        event="context",
        kind="frame",
        body={
            "pointer": "#/texts/42",
            "page_no": 3,
            "page_width": 600,
            "page_height": 800,
            "geometry": "coarse",
        },
    )
    for index, pointer in enumerate(("#/texts/42", "#/texts/43")):
        body = dict(
            kind="formula_outcomes", pointer=pointer, value=dict(pointer=pointer, outcome=outcome)
        )
        raw = json.dumps(body).encode()
        yield dict(
            event="companion_start", family="native_metadata", local_id=str(index), ordinal=index
        )
        yield dict(
            event="scalar_part",
            part=0,
            encoding="base64",
            value=base64.b64encode(raw).decode(),
            final=True,
        )
        yield dict(event="companion_end", byte_length=len(raw), sha256=sha256(raw).hexdigest())
    coverage = b'{"scope":"whole_document","outcome":"unknown"}'
    yield dict(event="companion_start", family="coverage", local_id="c", ordinal=0)
    yield dict(
        event="scalar_part",
        part=0,
        encoding="base64",
        value=base64.b64encode(coverage).decode(),
        final=True,
    )
    yield dict(
        event="companion_end", byte_length=len(coverage), sha256=sha256(coverage).hexdigest()
    )
    yield dict(
        event="outside_reference",
        body=dict(
            from_pointer="#/texts/42",
            field="caption",
            resolution="qualified_external",
            target=dict(
                task_id=69, product_key="native", content_digest="2" * 64, pointer="#/texts/99"
            ),
        ),
    )


@pytest.fixture
def offline_package(tmp_path):
    context = replace(
        prepare_interpretation_context(macros={}, kind="formula"), release_id="retained-release"
    )
    assert context.release_id is not None
    pin = PublishedSourcePin(
        project_id="p",
        run_id=7,
        selection_release_id=context.release_id,
        task_id=70,
        product_key="integrated",
        content_digest="1" * 64,
    )
    request = SelectedSourceExportRequest(
        pin=pin,
        selection=SelectedSourceSelection(root="#/groups/8"),
        destination=tmp_path / "package",
    )
    request.destination.mkdir()
    return request, context


def write_package(request, context, *, records=None, outcome="succeeded"):
    return _write_selected_package(
        SourceBytes(),
        source_events(records or independent_records(), outcome),
        request,
        request.destination,
        interpretation_model_id=context.model_id,
        implementation_digests=context.implementation_digests,
    )


def test_exact_offline_membership_table_original_addresses_and_formula_preparation(offline_package):
    request, context = offline_package
    receipt = write_package(request, context, records=independent_records(large=True))
    with SelectedSourceReader(
        request.destination, expected_pin=request.pin, expected_selection=request.selection
    ) as reader:
        prepared = reader.prepare_formula_inputs(context)
        assert [f.source.item_pointer for f in prepared.formulas] == ["#/texts/42", "#/texts/43"]
        assert [f.source.recognized_latex for f in prepared.formulas] == ["x=1", "x=1"]
        assert [f.source.original_text for f in prepared.formulas] == ["original A", "original B"]
        assert prepared.formulas[0].source.identity != prepared.formulas[1].source.identity
        assert reader.descriptors()[1]["body"]["geometry"] == "coarse"
        paths = list(reader._index.execute("SELECT pointer,path FROM records ORDER BY ordinal"))
        assert [row[0] for row in paths] == ["#/groups/8", "#/texts/42", "#/tables/2", "#/texts/43"]
        table = json.loads(Path(paths[2][1]).read_bytes())
        assert table["data"]["table_cells"][0]["text"] == "cell"
        assert receipt.selected_record_count == 4
        assert receipt.pin.selection_release_id == "retained-release"
        assert receipt.producer_release_id == "source-production-release"
        assert reader.header["producer_release_id"] == receipt.producer_release_id
        with pytest.raises(AdditionalContextRequired) as error:
            reader.prepare_formula_inputs(context, required_outside_values=["#/texts/99"])
        assert error.value.references[0]["target"]["content_digest"] == "2" * 64
    with pytest.raises(SelectedSourceUnavailable, match="closed"):
        reader.prepare_formula_inputs(context)


@pytest.mark.parametrize("outcome", ["failed", "unknown", "not_requested"])
def test_failed_or_unknown_recognition_publishes_no_prepared_input(offline_package, outcome):
    from corpus_structure.methods.math.pdf import FormulaRecognitionUnavailable

    request, context = offline_package
    write_package(request, context, outcome=outcome)
    with (
        SelectedSourceReader(request.destination) as reader,
        pytest.raises(FormulaRecognitionUnavailable),
    ):
        reader.prepare_formula_inputs(context)


@pytest.mark.parametrize(
    "change",
    [
        "root",
        "pin",
        "project",
        "omissions",
        "trailer",
        "scalar_boundary",
        "unicode",
        "unknown_event",
    ],
)
def test_altered_contract_or_incomplete_stream_is_refused(offline_package, change):
    request, context = offline_package
    write_package(request, context)
    path = request.destination / "events.jsonl"
    events = [json.loads(line) for line in path.read_bytes().splitlines()]
    if change in {"root", "pin", "project", "omissions"}:
        header = json.loads(events[0]["data"])
        if change == "root":
            header["selection"]["root"] = "#/groups/9"
        if change == "pin":
            header["pin"]["content_digest"] = "0" * 64
        if change == "project":
            header["pin"]["project_id"] = "other"
        if change == "omissions":
            header["omissions"] = []
        events[0]["data"] = json.dumps(header)
    elif change == "trailer":
        events.pop()
    elif change == "scalar_boundary":
        next(e for e in events if e["event"] == "scalar_part")["part"] = 1
    elif change == "unicode":
        next(e for e in events if e["event"] == "scalar_part")["value"] = base64.b64encode(
            b'"\xf0\x9f"'
        ).decode()
    else:
        events[1]["event"] = "unsupported_required_kind"
    path.write_bytes(b"\n".join(json.dumps(e).encode() for e in events) + b"\n")
    with pytest.raises((ValueError, SelectedSourceUnavailable)):
        SelectedSourceReader(request.destination)


def test_retained_context_binding_and_receipt_are_required(offline_package):
    request, context = offline_package
    write_package(request, context)
    with (
        SelectedSourceReader(request.destination) as reader,
        pytest.raises(SelectedSourceUnavailable, match="retained interpretation"),
    ):
        reader.prepare_formula_inputs(replace(context, model_id="new-default"))
    receipt_path = request.destination / "receipt.json"
    receipt = json.loads(receipt_path.read_bytes())
    receipt["byte_length"] += 1
    receipt_path.write_text(json.dumps(receipt))
    with pytest.raises(SelectedSourceUnavailable, match="receipt"):
        SelectedSourceReader(request.destination)


def test_early_native_source_failure_emits_no_complete_trailer_or_receipt(offline_package):
    request, context = offline_package

    def broken():
        for index, value in enumerate(source_events(independent_records())):
            if index == 3:
                raise OSError("owned source failed")
            yield value

    with pytest.raises(OSError, match="owned source failed"):
        _write_selected_package(
            SourceBytes(),
            broken(),
            request,
            request.destination,
            interpretation_model_id=context.model_id,
            implementation_digests=context.implementation_digests,
        )
    assert not (request.destination / "receipt.json").exists()
    assert b'"event":"trailer"' not in (request.destination / "events.jsonl").read_bytes()


def test_original_artifact_demand_is_an_explicit_input_requirement(offline_package):
    from corpus_structure.serve.selected_source import SelectedSourceInputRequired

    request, context = offline_package
    write_package(request, context)
    with (
        SelectedSourceReader(request.destination) as reader,
        pytest.raises(SelectedSourceInputRequired) as error,
    ):
        reader.prepare_formula_inputs(context, required_artifact_digests=["a" * 64])
    assert error.value.artifacts == (
        {"kind": "original", "sha256": "a" * 64, "availability": "not_included"},
    )


def test_large_scalar_uses_bounded_lines_and_owned_index_closes_on_abandonment(offline_package):
    request, context = offline_package
    records = independent_records()
    records[1]["body"]["caption"] = "😀" * 600000
    write_package(request, context, records=records)
    with (request.destination / "events.jsonl").open("rb") as source:
        assert max(len(line) for line in source) < 131072
    reader = SelectedSourceReader(request.destination)
    owned = reader._root
    reader.close()
    assert not owned.exists()
    with pytest.raises(SelectedSourceUnavailable, match="closed"):
        reader.descriptors()


def test_early_sink_failure_has_no_receipt_or_complete_trailer(offline_package, monkeypatch):
    request, context = offline_package
    original_open = Path.open

    class FailingSink:
        def __init__(self, stream):
            self.stream = stream
            self.calls = 0

        def __enter__(self):
            return self

        def __exit__(self, *_):
            self.stream.close()

        def write(self, body):
            self.calls += 1
            if self.calls == 3:
                raise OSError("sink abandoned")
            return self.stream.write(body)

    def open_path(path, mode="r", *args, **kwargs):
        stream = original_open(path, mode, *args, **kwargs)
        return FailingSink(stream) if path.name == "events.jsonl" and mode == "xb" else stream

    with monkeypatch.context() as patch:
        patch.setattr(Path, "open", open_path)
        with pytest.raises(OSError, match="sink abandoned"):
            write_package(request, context)
    assert not (request.destination / "receipt.json").exists()
    assert b'"event":"trailer"' not in (request.destination / "events.jsonl").read_bytes()
