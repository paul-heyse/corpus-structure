"""Independent selected-population expectations; these are not native custody claims."""

from pathlib import Path

import pytest

from corpus_structure.semantic.data_operation_compilation import compile_data_operations
from corpus_structure.semantic.data_operation_member_contracts import derive_member_kinds
from corpus_structure.semantic.native_source_view import thaw_native
from corpus_structure.semantic.prepare import prepare_release
from corpus_structure.semantic.source_discovery import (
    PreparedSourceDiscovery,
    selected_source_population,
    source_discovery_inputs,
    source_discovery_operation_sources,
)
from corpus_structure.semantic.source_products import FrozenNativeSource
from corpus_structure.semantic.types import SourceArtifact, SourceBundle


def test_source_discovery_reuses_exact_owned_schema_through_current_policy_composition():
    from corpus_structure.evaluate.declared_record_policy import record_policy_inputs
    from corpus_structure.semantic.prepare import _view

    core = Path(__file__).parents[2] / "src/corpus_structure/model/semantic/core.yaml"
    bundle = record_policy_inputs(
        SourceBundle("core", (SourceArtifact("core", core.read_bytes()),))
    )
    repeated = source_discovery_inputs(bundle)
    assert repeated == bundle
    assert repeated.root == "data_operation_record_policy_scope_root"
    assert "DdoSourceViewPopulation" in _view(repeated).all_classes()


def test_source_discovery_refuses_changed_owned_module_and_reserved_root():
    base = SourceBundle("core", (SourceArtifact("core", b"id: urn:core\nname: core\n"),))
    with pytest.raises(ValueError, match="differs from its acquired owner"):
        source_discovery_inputs(
            SourceBundle(
                base.root,
                (
                    *base.sources,
                    SourceArtifact(
                        "data_operation_source_discovery", b"id: urn:changed\nname: changed\n"
                    ),
                ),
            )
        )
    with pytest.raises(ValueError, match="reserved schema names"):
        source_discovery_inputs(
            SourceBundle(
                base.root,
                (
                    *base.sources,
                    SourceArtifact(
                        "data_operation_source_discovery_root",
                        b"id: urn:reserved\nname: reserved\n",
                    ),
                ),
            )
        )


@pytest.fixture(scope="module")
def profile():
    core = Path(__file__).parents[2] / "src/corpus_structure/model/semantic/core.yaml"
    bundle = source_discovery_inputs(
        SourceBundle("core", (SourceArtifact("core", core.read_bytes()),))
    )
    prepared = prepare_release(bundle)
    model = compile_data_operations(
        schema=bundle,
        python_sources=source_discovery_operation_sources(),
        definitions=prepared.definitions,
        vocabularies=prepared.vocabularies,
    )
    return PreparedSourceDiscovery(prepared, model)


def source(profile, *, document="document:one", start=0, end=4):
    items = [{"self_ref": "#/texts/0", "label": "text", "text": "mean", "orig": "mean"}]
    pieces = [
        {
            "kind": "native_text",
            "start": 0,
            "end": 4,
            "item_ref": "#/texts/0",
            "source_field": "text",
        }
    ]
    value = thaw_native(
        FrozenNativeSource.from_projection(
            profile.prepared,
            document=document,
            section_pointer="#/texts/0",
            membership="direct",
            text="mean",
            pieces=pieces,
            items=items,
        ).value
    )
    value["selectors"] = [{"projection": value["source"]["projection"], "start": start, "end": end}]
    return FrozenNativeSource.acquire(profile.prepared, value).value


def original():
    return {"document": "document:one", "content_hash": "0" * 64, "mime": "application/pdf"}


def test_closed_empty_source_selection_is_explicit_and_has_nominal_members(profile):
    import json

    population = json.loads(profile.project(original(), (), True).content)
    assert population == {"document": "document:one", "complete": True, "members": []}
    kind = profile.prepared.index.definitions["DdoSourceViewPopulation"].iri
    assert derive_member_kinds(profile.model, kind) == (
        profile.prepared.index.definitions["DdoSelectedNativeSource"].iri,
    )
    operation = profile.model.operation("source.selected_views/discovery")
    assert operation.profile == "discovery"
    assert (
        operation.capabilities.prepared_factory.entrypoint
        == "corpus_structure.methods.source_discovery.SelectedSourceViewsOperation.acquire_port"
    )


def test_source_discovery_preserves_scoped_members_and_partial_standing(profile):
    import json

    first, second = source(profile, end=2), source(profile, start=2)
    population = json.loads(profile.project(original(), (second, first), False).content)
    assert population["complete"] is False
    assert {member["body"]["text"] for member in population["members"]} == {"mean"}
    assert len({member["member_id"] for member in population["members"]}) == 2
    assert len({member["context"]["subject"] for member in population["members"]}) == 1
    assert {
        tuple(
            (selector["start"], selector["end"])
            for selector in member["context"]["analyzed_scope"]["selectors"]
        )
        for member in population["members"]
    } == {((0, 2),), ((2, 4),)}
    assert all(
        member["context"]["original_source"] == "document:one" for member in population["members"]
    )
    assert (
        profile.project(original(), (first, second), False).content
        == profile.project(original(), (second, first), False).content
    )


def test_source_discovery_refuses_foreign_original_and_repeated_complete_context(profile):
    view = source(profile)
    with pytest.raises(ValueError, match="different original documents"):
        profile.project(original(), (source(profile, document="document:other"),), True)
    with pytest.raises(ValueError, match="repeats a complete selected source context"):
        profile.project(original(), (view, view), True)
    with pytest.raises(TypeError, match="explicit complete/partial"):
        selected_source_population(original(), (), complete=1, kind_contract="kind:test")


def test_native_source_keeps_original_key_and_canonical_document_address(profile):
    from corpus_structure.semantic.original_documents import original_document_subject

    value = thaw_native(source(profile))
    assert value["source"]["document"] == "document:one"
    assert value["source"]["document_subject"] == original_document_subject("document:one")
    assert value["source"]["document_subject"] != value["source"]["document"]
    value["source"]["document_subject"] = original_document_subject("document:other")
    with pytest.raises(ValueError, match="document address differs"):
        FrozenNativeSource.acquire(profile.prepared, value)


def test_acquire_preserves_body_under_its_older_pinned_source_contract(profile):
    import yaml

    from corpus_structure.semantic.source_products import source_product_inputs

    core = Path(__file__).parents[2] / "src/corpus_structure/model/semantic/core.yaml"
    bundle = source_product_inputs(
        SourceBundle("core", (SourceArtifact("core", core.read_bytes()),))
    )
    old_sources = []
    for artifact in bundle.sources:
        if artifact.name == "data_operation_source":
            old = yaml.safe_load(artifact.content)
            del old["classes"]["DdoNativeSourceCoordinate"]["attributes"]["document_subject"]
            artifact = SourceArtifact(artifact.name, yaml.safe_dump(old).encode())
        old_sources.append(artifact)
    older = prepare_release(SourceBundle(bundle.root, tuple(old_sources)))
    value = thaw_native(source(profile))
    del value["source"]["document_subject"]
    preserved = FrozenNativeSource.acquire(older, value)
    assert thaw_native(preserved.value) == value
    assert "document_subject" not in preserved.value["source"]


def test_discovery_views_require_computational_origin_and_exact_frozen_source_set(profile):
    operation = profile.model.operation("source.selected_views/discovery")
    role = next(role for role in operation.roles if role.name == "views")
    assert role.support.origins == ("computation",)
    assert role.support.identity_requirements == ("episode",)
    assert role.support.source == "frozen-source-set"
    assert role.support.source_set == "selected-source-views"
    assert role.subject_field == "/source/document_subject"


def test_source_hierarchy_preserves_distinct_computational_member_addresses(profile):
    from corpus_structure.semantic.acquired_selected_relations import LiveSelectedRelations
    from corpus_structure.semantic.data_operation_json import json_bytes, json_loads
    from corpus_structure.semantic.data_operation_values import semantic_value
    from corpus_structure.semantic.demand_results import CutSelection
    from corpus_structure.semantic.source_hierarchy_graph import source_hierarchy_snapshot

    kind = next(
        item.key
        for item in profile.model.identities
        if item.domain == "kind"
        and item.owner == profile.prepared.index.definitions["DdoSelectedNativeSource"].iri
    )
    index = LiveSelectedRelations()
    try:
        for member, value in (
            ("first", source(profile, end=2)),
            ("second", source(profile, start=2)),
        ):
            row = dict(
                product_id="actual-container",
                member_id=member,
                kind_contract=kind,
                body=semantic_value(value),
            )
            index.append(
                json_bytes(
                    dict(key="member:" + member, relation="kb.data_product_member", record=row)
                )
            )
        cut = CutSelection(
            json_bytes(
                {
                    "project_id": "project",
                    "release_id": "release",
                    "demand_id": "demand",
                    "runtime_id": "runtime",
                    "read_id": "read",
                    "read_snapshot": "1:1:",
                    "frontier_at": "2026-11-15T00:00:00Z",
                    "scope": {},
                    "selection": {
                        "version": "data-demand-public-selection-v1",
                        "model": "0" * 64,
                        "intent_digest": "intent:source",
                        "roots": [],
                        "targets": ["source.selected_views/discovery"],
                        "root_operations": ["source.selected_views/discovery"],
                        "discovery": [],
                    },
                    "trust_snapshot": {},
                }
            )
        )
        snapshot = source_hierarchy_snapshot(profile.prepared, profile.model, cut, index)
        assert len(snapshot.nodes) == 2 and len({row.identity for row in snapshot.nodes}) == 2
        assert {json_loads(row.payload_json)["member_id"] for row in snapshot.nodes} == {
            "first",
            "second",
        }
        assert all(
            json_loads(row.payload_json)["product_id"] == "actual-container"
            for row in snapshot.nodes
        )
        assert all(
            json_loads(row.payload_json)["atom"]["self_ref"] == "#/texts/0"
            for row in snapshot.nodes
        )
    finally:
        index.close()
