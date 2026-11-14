"""Independent selected-population expectations; these are not native custody claims."""

from pathlib import Path

import pytest

from corpus_structure.semantic import SourceArtifact, SourceBundle, prepare_release
from corpus_structure.semantic.data_operation_compilation import compile_data_operations
from corpus_structure.semantic.data_operation_member_contracts import derive_member_kinds
from corpus_structure.semantic.source_discovery import (
    PreparedSourceDiscovery,
    selected_source_population,
    source_discovery_inputs,
    source_discovery_operation_sources,
)
from corpus_structure.semantic.source_products import FrozenNativeSource


@pytest.fixture(scope="module")
def profile():
    core = Path(__file__).parents[2] / "src/corpus_structure/model/semantic/core.yaml"
    bundle = source_discovery_inputs(SourceBundle("core", (SourceArtifact("core", core.read_bytes()),)))
    prepared = prepare_release(bundle)
    model = compile_data_operations(schema=bundle, python_sources=source_discovery_operation_sources(), definitions=prepared.definitions, vocabularies=prepared.vocabularies)
    return PreparedSourceDiscovery(prepared, model)


def source(profile, *, document="document:one", start=0, end=4):
    items = [{"self_ref": "#/texts/0", "label": "text", "text": "mean", "orig": "mean"}]
    pieces = [{"kind": "native_text", "start": 0, "end": 4, "item_ref": "#/texts/0", "source_field": "text"}]
    value = FrozenNativeSource.from_projection(profile.prepared, document=document, section_pointer="#/texts/0", membership="direct", text="mean", pieces=pieces, items=items).value
    value["selectors"] = [{"projection": value["source"]["projection"], "start": start, "end": end}]
    return FrozenNativeSource.acquire(profile.prepared, value).value


def original():
    return {"document": "document:one", "content_hash": "0" * 64, "mime": "application/pdf"}


def test_closed_empty_source_selection_is_explicit_and_has_nominal_members(profile):
    import json

    population = json.loads(profile.project(original(), (), True).content)
    assert population == {"document": "document:one", "complete": True, "members": []}
    kind = profile.prepared.index.definitions["DdoSourceViewPopulation"].iri
    assert derive_member_kinds(profile.model, kind) == (profile.prepared.index.definitions["DdoSelectedNativeSource"].iri,)
    operation = profile.model.operation("source.selected_views/discovery")
    assert operation.profile == "discovery"
    assert operation.capabilities.prepared_factory.entrypoint == "corpus_structure.methods.source_discovery.SelectedSourceViewsOperation.acquire_port"


def test_source_discovery_preserves_scoped_members_and_partial_standing(profile):
    import json

    first, second = source(profile, end=2), source(profile, start=2)
    population = json.loads(profile.project(original(), (second, first), False).content)
    assert population["complete"] is False
    assert {member["body"]["text"] for member in population["members"]} == {"mean"}
    assert len({member["member_id"] for member in population["members"]}) == 2
    assert len({member["context"]["subject"] for member in population["members"]}) == 1
    assert {tuple((selector["start"], selector["end"]) for selector in member["context"]["analyzed_scope"]["selectors"]) for member in population["members"]} == {((0, 2),), ((2, 4),)}
    assert all(member["context"]["original_source"] == "document:one" for member in population["members"])
    assert profile.project(original(), (first, second), False).content == profile.project(original(), (second, first), False).content


def test_source_discovery_refuses_foreign_original_and_repeated_complete_context(profile):
    view = source(profile)
    with pytest.raises(ValueError, match="different original documents"):
        profile.project(original(), (source(profile, document="document:other"),), True)
    with pytest.raises(ValueError, match="repeats a complete selected source context"):
        profile.project(original(), (view, view), True)
    with pytest.raises(TypeError, match="explicit complete/partial"):
        selected_source_population(original(), (), complete=1, kind_contract="kind:test")
