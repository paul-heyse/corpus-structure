"""Independent metadata refusals preserve authenticated native cut material."""

from copy import deepcopy
from decimal import Decimal

import pytest
from pydantic import ValidationError

from corpus_structure.semantic.data_operation_json import json_bytes
from corpus_structure.semantic.demand_results import CutSelection
from corpus_structure.serve.demand_export_manifest import (
    checked_export_manifest,
    decode_export_manifest,
)
from semantic.demand_result_support import demand_result_page


def manifest():
    page = demand_result_page()
    page["selection"]["roots"] = [
        {"subject": "doc", "original_source": "source:A", "analyzed_scope": {"scale": Decimal("1.20")}}
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
    assert json_bytes(checked_export_manifest(source)) == before
    result = decode_export_manifest(before)
    assert json_bytes(result) == before
    assert result["cut"]["selection"]["roots"][0]["analyzed_scope"] == {
        "scale": Decimal("1.20")
    }
    assert CutSelection(json_bytes(result["cut"])).identity == source["cut_id"]
    source["pages"].clear()
    assert result["pages"] == ["page.json"]


@pytest.mark.parametrize("damage", ["extra", "fractional-count", "bool-count", "missing-file", "escape", "cut"])
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
    with pytest.raises(ValueError, match="invalid native JSON"):
        decode_export_manifest(b'{"format":"demand-result-export-v3","format":"other"}')
