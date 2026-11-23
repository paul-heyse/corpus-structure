"""Independent metadata refusals preserve authenticated native cut material."""

from copy import deepcopy
from decimal import Decimal
from hashlib import sha256
from typing import Any

import pytest
from pydantic import ValidationError

from corpus_structure.semantic.data_operation_json import json_bytes
from corpus_structure.semantic.demand_results import CutSelection
from corpus_structure.serve.demand_export_manifest import (
    checked_export_manifest,
    decode_export_manifest,
)
from semantic.demand_result_support import demand_result_page


def manifest() -> dict[str, Any]:
    page = demand_result_page()
    page["selection"]["roots"] = [
        {
            "subject": "doc",
            "original_source": "source:A",
            "analyzed_scope": {"scale": Decimal("1.20")},
        }
    ]
    cut = CutSelection.from_native(page)
    names = ["page.json", "closure.jsonl", "reader.json", "authority.json", "execution.json"]
    return {
        "format": "demand-result-export-v3",
        "encoding": "jsonl",
        "cut_id": cut.identity,
        "cut": cut.record,
        "pages": ["page.json"],
        "closure": "closure.jsonl",
        "reader_contract": "reader.json",
        "authority_contract": "authority.json",
        "execution_evidence_contract": "execution.json",
        "support_disclosure": "complete",
        "execution_evidence_disclosure": "complete",
        "releases": {},
        "runtimes": [],
        "source_artifacts": {},
        "relations": {},
        "files": {name: {"bytes": 10, "sha256": "a" * 64} for name in names},
        "trust": "selected historical acquisition; current trust requires native reassessment",
    }


def test_manifest_validation_preserves_v3_bytes_and_contextual_cut():
    source = manifest()
    before = json_bytes(source)
    assert checked_export_manifest(source).to_bytes() == before
    result = decode_export_manifest(before)
    assert result.to_bytes() == before
    assert result.cut["selection"]["roots"][0]["analyzed_scope"] == {"scale": Decimal("1.20")}
    assert result.cut_selection.identity == source["cut_id"]
    source["pages"].clear()
    assert result.pages == ["page.json"]


@pytest.mark.parametrize(
    "damage", ["extra", "fractional-count", "bool-count", "missing-file", "escape", "cut"]
)
def test_manifest_refuses_independently_damaged_framing(damage):
    source = deepcopy(manifest())
    if damage == "extra":
        source["unmodeled"] = True
    elif damage == "fractional-count":
        source["files"]["page.json"]["bytes"] = Decimal("10.0")
    elif damage == "bool-count":
        source["files"]["page.json"]["bytes"] = True
    elif damage == "missing-file":
        source["pages"] = ["unlisted.json"]
    elif damage == "escape":
        source["files"]["../outside"] = {"bytes": 0, "sha256": "a" * 64}
    else:
        source["cut_id"] = "cut-selection:foreign"
    with pytest.raises((ValidationError, ValueError)):
        checked_export_manifest(source)


def test_manifest_decoder_refuses_duplicate_keys_before_validation():
    with pytest.raises(ValueError, match="invalid retained JSON"):
        decode_export_manifest(b'{"format":"demand-result-export-v3","format":"other"}')


def test_manifest_writer_embeds_the_actual_cut_bytes_and_detaches_the_interpretation():
    from semantic.test_frontier_json_policy import expect_roles, frontier

    original = CutSelection.from_native(frontier())
    cut = CutSelection(original.content.replace(b'":', b'": '))
    metadata = manifest()
    metadata.pop("cut")
    metadata["cut_id"] = cut.identity
    checked = checked_export_manifest(metadata, cut=cut)
    expected = json_bytes({**metadata, "cut": "CUT_BYTES"}).replace(
        b'"cut":"CUT_BYTES"', b'"cut":' + cut.content
    )
    assert checked.to_bytes() == expected
    assert checked.cut_selection.content == cut.content
    expect_roles(checked.cut)
    restored = decode_export_manifest(expected)
    assert restored.to_bytes() == expected
    assert restored.cut_selection.content == cut.content
    assert restored.cut_selection.identity == cut.identity
    expect_roles(restored.cut)


def test_historical_manifest_preserves_its_full_framing_bytes():
    original = json_bytes(manifest()).replace(b',"encoding":', b',\n  "encoding":')
    decoded = decode_export_manifest(original)
    assert decoded.to_bytes() == original


def test_archive_writer_preserves_declared_nested_arrow_fields(tmp_path):
    import pyarrow as pa
    import pyarrow.parquet as pq

    from corpus_structure.serve.selected_archive_relations import (
        ARCHIVE_KEY,
        write_support_fragments,
    )

    schema = pa.schema(
        [
            pa.field(ARCHIVE_KEY, pa.string(), nullable=False),
            pa.field("dependencies", pa.list_(pa.field("item", pa.string(), nullable=False))),
        ]
    )
    packet = {
        "key": "ops.example:0",
        "relation": "ops.example",
        "record": {"dependencies": ["first", "second"]},
    }
    [(_, path, count)] = write_support_fragments(
        tmp_path, [packet], lambda _: (schema, {"dependencies": "native"}), batch_bytes=1024
    )
    with pq.ParquetFile(path) as fragment:
        assert fragment.schema_arrow.equals(schema, check_metadata=True)
        assert fragment.read().column("dependencies").to_pylist() == [["first", "second"]]
    assert count == 1


def test_archive_scan_custody_owns_the_bytes_it_verified(tmp_path):
    from corpus_structure.serve.archive_custody import acquire_demand_archive

    source = manifest()
    original = b"verified bytes"
    source["files"] = {
        name: {"bytes": len(original), "sha256": sha256(original).hexdigest()}
        for name in source["files"]
    }
    for name in source["files"]:
        (tmp_path / name).write_bytes(original)
    content = json_bytes(source)
    (tmp_path / "manifest.json").write_bytes(content)
    expected = sha256(content).hexdigest()
    selected = tmp_path / "closure.jsonl"
    with acquire_demand_archive(tmp_path, expected, decode_export_manifest) as (owned, _):
        substitute = tmp_path / "substitute"
        substitute.write_bytes(b"new pathname!!")
        substitute.replace(selected)
        assert (owned / selected.name).read_bytes() == original
        selected.write_bytes(b"in-place edit!")
        assert (owned / selected.name).read_bytes() == original
    assert not owned.exists()
    with (
        pytest.raises(ValueError, match="pinned manifest"),
        acquire_demand_archive(tmp_path, expected, decode_export_manifest),
    ):
        pytest.fail("changed bytes received custody")


def test_v3_closure_transcodes_into_the_common_typed_reader(tmp_path):
    import pyarrow as pa

    from corpus_structure.semantic.selected_support_contract import SelectedSupportReader
    from corpus_structure.serve.demand_export import _support_fragments
    from corpus_structure.serve.selected_archive_relations import ArchivedSelectedRelations

    source = manifest()
    captured = checked_export_manifest(source)
    relation = "ops.example"
    schema = pa.schema([pa.field("id", pa.string()), pa.field("context", pa.json_())])
    contract = {
        "schema": {
            "$schema": "http://json-schema.org/draft-07/schema#",
            "type": "object",
            "required": ["id", "context"],
            "properties": {"id": {"type": "string"}, "context": {}},
        },
        "contextual_fields": ["#/properties/context"],
        "encodings": {"id": "native", "context": "json"},
        "arrow_schema": schema.serialize().to_pybytes().hex(),
    }
    packets = [
        {"key": "ops.example:0", "relation": relation, "record": {"id": "a", "context": {"n": 1}}},
        {
            "key": "ops.example:1",
            "relation": relation,
            "record": {"id": "b", "context": {"n": Decimal("1.20")}},
        },
    ]
    (tmp_path / "closure.jsonl").write_bytes(b"".join(json_bytes(row) + b"\n" for row in packets))
    scratch = tmp_path / "scratch"
    scratch.mkdir()
    fragments = _support_fragments(tmp_path, captured, {relation: contract}, scratch)
    archived = ArchivedSelectedRelations(fragments, SelectedSupportReader({relation: contract}))
    archived.validate_support()
    assert list(archived.records()) == packets
    record = archived.mapping(relation, ("id",))["b"]
    assert isinstance(record["context"]["n"], Decimal)
    assert record["context"]["n"].as_tuple().exponent == -2


@pytest.mark.parametrize("mutate", ["cut", "files"])
def test_manifest_emission_refuses_mutated_interpretation_or_metadata(mutate):
    decoded = decode_export_manifest(json_bytes(manifest()))
    if mutate == "cut":
        decoded.cut["read_id"] = "different"
    else:
        decoded.files["page.json"].bytes += 1
    with pytest.raises(ValueError, match="changed after validation"):
        decoded.to_bytes()
