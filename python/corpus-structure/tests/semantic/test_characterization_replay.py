"""Surviving primary-layer review contracts authenticate sources and released policy.

The retired task/layer detached envelope is not a second selected export route.
"""

from copy import deepcopy

import pytest

from corpus_structure.semantic.characterization import characterization_inputs
from corpus_structure.serve.primary_characterization_replay import _authenticate_contract, validate_captured_layer_sources
from semantic.characterization_replay_support import prepared as prepared, contract_data


@pytest.mark.parametrize("mutation", [None, "schema", "policy", "sources", "release"])
def test_primary_contract_recompiles_actual_released_inputs_and_rejects_resealed_claims(prepared, mutation):
    from pathlib import Path
    from corpus_structure.semantic import SourceArtifact, SourceBundle
    core = Path(__file__).parents[2] / "src/corpus_structure/model/semantic/core.yaml"
    sources = characterization_inputs(SourceBundle("core", (SourceArtifact("core", core.read_bytes()),)))
    contract = contract_data(prepared, sources)
    if mutation == "schema":
        contract["schemas"]["AnnotationLayer"]["title"] = "Forged released schema"
    elif mutation == "policy":
        contract["attachment_policies"]["invented"] = {"class_name": "Forged"}
    elif mutation == "sources":
        contract["sources"]["core"] = "eA=="
    elif mutation == "release":
        contract["release_id"] = "release:invented"
    if mutation is not None:
        with pytest.raises(ValueError):
            _authenticate_contract(contract, prepared.manifest)
    else:
        checked = _authenticate_contract(contract, prepared.manifest)
        assert checked.release_id == prepared.release_id
        assert checked.json_schema("AnnotationLayer") == prepared.json_schema("AnnotationLayer")


def source_and_layer():
    reference = dict(key="source:selected", native_product={"task_id": 7, "product_key": "raw", "content_digest": "a"*64},
        section_pointer="#/body", membership="members:exact", projection_digest="projection:exact", recipe_digest="recipe:exact")
    source = dict(source_view_id=5, ref=reference, text="all", context=dict(
        items=[{"self_ref": "#/texts/0", "prov": [{"page_no": 3}]}],
        pieces=[{"kind": "native_text", "item_ref": "#/texts/0", "start": 0, "end": 3}]))
    selector = dict(projection="projection:exact", native_pointer="#/texts/0", page=3, start=0, end=3)
    body = dict(source_scope={"source_view_ids": [5], "source_views": [{"source_view_id": 5, **{key: value for key, value in reference.items() if key != "native_product"}, "base_document": reference["native_product"]}], "selectors": [selector]},
        coverage=[{"eligible": [selector], "examined": [selector], "unexamined": []}],
        occurrences=[{"extents": [{"source_view_id": 5, "native_pointer": "#/texts/0", "page": 3,
            "start": 0, "end": 3, "text": "all", "synthetic": False}]}])
    return source, body


@pytest.mark.parametrize("mutation", [None, "view-pin", "pointer", "page", "projection", "literal", "range"])
def test_primary_source_authentication_preserves_coordinate_authority_and_literal_proof(mutation):
    source, body = source_and_layer()
    if mutation == "view-pin":
        body["source_scope"]["source_views"][0]["key"] = "source:foreign"
    elif mutation in {"pointer", "page", "projection"}:
        field, value = {"pointer": ("native_pointer", "#/texts/99"), "page": ("page", 99), "projection": ("projection", "foreign")}[mutation]
        body["coverage"][0]["examined"] = [{**deepcopy(body["source_scope"]["selectors"][0]), field: value}]
    elif mutation == "literal":
        body["occurrences"][0]["extents"][0]["text"] = "not all"
    elif mutation == "range":
        body["occurrences"][0]["extents"][0]["end"] = 4
    if mutation is not None:
        with pytest.raises(ValueError):
            validate_captured_layer_sources(body, {5: source})
    else:
        validate_captured_layer_sources(body, {5: source})
        assert body["occurrences"][0]["extents"][0]["text"] == "all"
