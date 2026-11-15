"""Independent selected graph policy and missing-custody controls."""

from types import SimpleNamespace

import pytest

from corpus_structure.semantic.data_operation_json import json_bytes
from corpus_structure.semantic.data_operation_read_index import SelectedRecordIndex
from corpus_structure.semantic.demand_results import CutSelection
from corpus_structure.semantic.selected_graph import snapshot_from_index
from semantic.data_operation_declaration_support import model, operation


def selected_index(tmp_path):
    index = SelectedRecordIndex(tmp_path / "index.sqlite")
    pins = dict(demand_id="demand", project_id="project", release_id="release", runtime_id="runtime", selection={}, trust_snapshot={}, read_id="read", read_snapshot="snapshot", frontier_at="time", scope={})
    index.append_page(dict(**pins, obligations=[dict(obligation_id="obligation",operation_id="consumer",request_id="consumer")], uses=[dict(use_id="cu",request_id="consumer",derivation_id="ce",selection=dict(support=[dict(kind="computation",derivation_id="new",admission_use_id="su",role="value",position=7)],populations=[]))]))
    rows = {
        "ops.data_request": [dict(id="consumer"),dict(id="producer")],
        "ops.demand_use": [dict(id="cu",request_id="consumer",derivation_id="ce",selection=dict(support=[dict(kind="computation",derivation_id="new",admission_use_id="su",role="value",position=7)],populations=[])),dict(id="su",request_id="producer",derivation_id="new",selection=dict(support=[],populations=[]))],
        "ops.data_derivation": [dict(id="ce",request_id="consumer"),dict(id="old",request_id="producer"),dict(id="new",request_id="producer")],
        "ops.data_derivation_support": [dict(derivation_id="ce",support_derivation_id="old",occurrence=0,role="value")],
    }
    for relation, records in rows.items():
        for ordinal, row in enumerate(records):
            index.append(json_bytes(dict(key=relation+":"+str(ordinal),relation=relation,record=row)))
    return index, CutSelection(json_bytes(pins))


def test_bound_precedence_and_selected_support_are_distinct_projections(tmp_path,monkeypatch):
    from corpus_structure.semantic import data_operation_admission
    compiled = model(operation("operation"))
    monkeypatch.setattr(data_operation_admission,"bound_data_operation_model",lambda prepared: compiled)
    index,cut = selected_index(tmp_path)
    prepared=SimpleNamespace(release_id="release")
    try:
        requests=snapshot_from_index(prepared,cut,index,"bound-requests")
        assert {node.kind for node in requests.nodes} == {"request","use","obligation"}
        assert any(edge.source=='ops.demand_use:"cu"' and edge.target=='ops.data_request:"producer"' and edge.relation=="selected-input" for edge in requests.occurrences)
        support=snapshot_from_index(prepared,cut,index,"selected-support")
        assert {node.kind for node in support.nodes} == {"episode","use"}
        assert any(edge.source=='ops.demand_use:"cu"' and edge.target=='ops.demand_use:"su"' and edge.relation=="support" for edge in support.occurrences)
        assert next(edge for edge in support.occurrences if edge.relation=="support").position==7
        assert not any(edge.source=='ops.data_derivation:"ce"' and edge.target=='ops.data_derivation:"old"' for edge in support.occurrences)
    finally:
        index.close()


def test_required_selected_reference_cannot_disappear_silently(tmp_path,monkeypatch):
    from corpus_structure.semantic import data_operation_admission
    monkeypatch.setattr(data_operation_admission,"bound_data_operation_model",lambda prepared: model(operation("operation")))
    index,cut=selected_index(tmp_path)
    index.connection.execute("DELETE FROM records WHERE relation='ops.demand_use' AND json_extract(payload,'$.record.id')='su'")
    try:
        with pytest.raises(ValueError,match="required.*support use"):
            snapshot_from_index(SimpleNamespace(release_id="release"),cut,index,"selected-support")
    finally:
        index.close()


def test_pinned_frontier_rejects_conflicting_pages(tmp_path):
    index,cut=selected_index(tmp_path)
    try:
        with pytest.raises(ValueError,match="different native cuts"):
            index.append_page({**cut.record, "obligations": [], "uses": [], "read_id": "other"})
    finally:
        index.close()
