"""Independent metadata refusals preserve authenticated native cut material."""

from copy import deepcopy
from decimal import Decimal
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


@pytest.mark.parametrize("mutate", ["cut", "files"])
def test_manifest_emission_refuses_mutated_interpretation_or_metadata(mutate):
    decoded = decode_export_manifest(json_bytes(manifest()))
    if mutate == "cut":
        decoded.cut["read_id"] = "different"
    else:
        decoded.files["page.json"].bytes += 1
    with pytest.raises(ValueError, match="changed after validation"):
        decoded.to_bytes()
