"""Independent selected graph policy and missing-custody controls."""

import json
from types import SimpleNamespace

import pytest

from corpus_structure.semantic.data_operation_json import json_bytes
from corpus_structure.semantic.data_operation_read_index import SelectedRecordIndex
from corpus_structure.semantic.demand_results import CutSelection
from corpus_structure.semantic.selected_graph import snapshot_from_index
from semantic.data_operation_declaration_support import model, operation


def test_selected_index_binds_unindexed_fields_and_uses_declared_expression_indexes(tmp_path):
    from corpus_structure.semantic.data_operation_read_index import _selected

    index = SelectedRecordIndex(tmp_path / "expressions.sqlite")
    value = "literal '%[0]"
    record = dict.fromkeys(
        (
            "id",
            "kind_contract",
            "product_id",
            "member_id",
            "derivation_id",
            "role",
            "position",
            "occurrence",
            "alternate",
        ),
        value,
    )
    groups = (
        ("id",),
        ("kind_contract",),
        ("product_id", "member_id"),
        ("derivation_id", "role", "position"),
        ("derivation_id", "occurrence"),
    )
    try:
        index.append(json_bytes(dict(relation="sample", key="unique", record=record)))
        for fields in (*groups, ("alternate",)):
            values = (value,) * len(fields)
            statement = _selected("sample", fields, values)
            compiled = statement.compile(
                index.connection, compile_kwargs={"render_postcompile": True}
            )
            plan = index.connection.exec_driver_sql(
                "EXPLAIN QUERY PLAN " + str(compiled),
                tuple(compiled.params[name] for name in (compiled.positiontup or ())),
            ).all()
            if fields in groups:
                assert any("record_" + "_".join(fields) + " (" in detail for *_, detail in plan)
                assert any("<expr>=?" in detail for *_, detail in plan)
            else:
                assert "alternate" not in str(compiled)
                assert "$.record.alternate" in compiled.params.values()
                assert all("<expr>=?" not in detail for *_, detail in plan)
            key = values[0] if len(fields) == 1 else values
            assert index.mapping("sample", fields)[key] == record
    finally:
        index.close()


def selected_index(tmp_path):
    index = SelectedRecordIndex(tmp_path / "index.sqlite")
    pins = dict(
        demand_id="demand",
        project_id="project",
        release_id="release",
        runtime_id="runtime",
        selection={},
        trust_snapshot={},
        read_id="read",
        read_snapshot="snapshot",
        frontier_at="time",
        scope={},
    )
    index.append_page(
        dict(
            **pins,
            obligations=[
                dict(obligation_id="obligation", operation_id="consumer", request_id="consumer")
            ],
            uses=[
                dict(
                    use_id="cu",
                    request_id="consumer",
                    derivation_id="ce",
                    selection=dict(
                        support=[
                            dict(
                                kind="computation",
                                derivation_id="new",
                                admission_use_id="su",
                                role="value",
                                position=7,
                            )
                        ],
                        populations=[],
                    ),
                )
            ],
        )
    )
    rows = {
        "ops.data_request": [dict(id="consumer"), dict(id="producer")],
        "ops.demand_use": [
            dict(
                id="cu",
                request_id="consumer",
                derivation_id="ce",
                selection=dict(
                    support=[
                        dict(
                            kind="computation",
                            derivation_id="new",
                            admission_use_id="su",
                            role="value",
                            position=7,
                        )
                    ],
                    populations=[],
                ),
            ),
            dict(
                id="su",
                request_id="producer",
                derivation_id="new",
                selection=dict(support=[], populations=[]),
            ),
        ],
        "ops.data_derivation": [
            dict(id="ce", request_id="consumer"),
            dict(id="old", request_id="producer"),
            dict(id="new", request_id="producer"),
        ],
        "ops.data_derivation_support": [
            dict(derivation_id="ce", support_derivation_id="old", occurrence=0, role="value")
        ],
    }
    for relation, records in rows.items():
        for ordinal, row in enumerate(records):
            index.append(
                json_bytes(dict(key=relation + ":" + str(ordinal), relation=relation, record=row))
            )
    return index, CutSelection(json_bytes(pins))


def test_bound_precedence_and_selected_support_are_distinct_projections(tmp_path, monkeypatch):
    from corpus_structure.semantic import data_operation_admission

    compiled = model(operation("operation"))
    monkeypatch.setattr(
        data_operation_admission, "bound_data_operation_model", lambda prepared: compiled
    )
    index, cut = selected_index(tmp_path)
    prepared = SimpleNamespace(release_id="release")
    try:
        requests = snapshot_from_index(prepared, cut, index, "bound-requests")
        assert {node.kind for node in requests.nodes} == {"request", "use", "obligation"}
        assert any(
            edge.source == 'ops.demand_use:"cu"'
            and edge.target == 'ops.data_request:"producer"'
            and edge.relation == "selected-input"
            for edge in requests.occurrences
        )
        support = snapshot_from_index(prepared, cut, index, "selected-support")
        assert {node.kind for node in support.nodes} == {"episode", "use"}
        assert any(
            edge.source == 'ops.demand_use:"cu"'
            and edge.target == 'ops.demand_use:"su"'
            and edge.relation == "support"
            for edge in support.occurrences
        )
        assert (
            next(edge for edge in support.occurrences if edge.relation == "support").position == 7
        )
        assert not any(
            edge.source == 'ops.data_derivation:"ce"' and edge.target == 'ops.data_derivation:"old"'
            for edge in support.occurrences
        )
    finally:
        index.close()


def test_required_selected_reference_cannot_disappear_silently(tmp_path, monkeypatch):
    from corpus_structure.semantic import data_operation_admission

    monkeypatch.setattr(
        data_operation_admission,
        "bound_data_operation_model",
        lambda prepared: model(operation("operation")),
    )
    index, cut = selected_index(tmp_path)
    index.connection.exec_driver_sql(
        "DELETE FROM records WHERE relation='ops.demand_use' AND json_extract(payload,'$.record.id')='su'"
    )
    try:
        with pytest.raises(ValueError, match=r"required.*support use"):
            snapshot_from_index(
                SimpleNamespace(release_id="release"), cut, index, "selected-support"
            )
    finally:
        index.close()


def test_pinned_frontier_rejects_conflicting_pages(tmp_path):
    index, cut = selected_index(tmp_path)
    try:
        with pytest.raises(ValueError, match="different native cuts"):
            index.append_page({**cut.record, "obligations": [], "uses": [], "read_id": "other"})
    finally:
        index.close()


def test_authored_admission_is_not_relabelled_original_source(tmp_path, monkeypatch):
    from corpus_structure.semantic import data_operation_admission

    monkeypatch.setattr(
        data_operation_admission,
        "bound_data_operation_model",
        lambda prepared: model(operation("operation")),
    )
    index, cut = selected_index(tmp_path)
    try:
        for relation, row in [
            ("kb.data_product", dict(id="authored-product")),
            (
                "ops.original_source_admission",
                dict(
                    id="authored", product_id="authored-product", evidence=dict(standing="authored")
                ),
            ),
        ]:
            index.append(
                json_bytes(dict(key=relation + ":authored", relation=relation, record=row))
            )
        snapshot = snapshot_from_index(
            SimpleNamespace(release_id="release"), cut, index, "selected-support"
        )
        assert (
            next(
                node
                for node in snapshot.nodes
                if node.identity == 'ops.original_source_admission:"authored"'
            ).kind
            == "authored"
        )
    finally:
        index.close()


@pytest.mark.parametrize("fate", ["awaiting-population", "unavailable"])
def test_requestless_recorded_fate_preserves_obligation_and_use(tmp_path, monkeypatch, fate):
    from corpus_structure.semantic import data_operation_admission

    monkeypatch.setattr(
        data_operation_admission,
        "bound_data_operation_model",
        lambda prepared: model(operation("operation")),
    )
    index = SelectedRecordIndex(tmp_path / "requestless.sqlite")
    pins = dict(
        demand_id="demand",
        project_id="project",
        release_id="release",
        runtime_id="runtime",
        selection={},
        trust_snapshot={},
        read_id="read",
        read_snapshot="snapshot",
        frontier_at="time",
        scope={},
    )
    try:
        index.append_page(
            dict(
                **pins,
                obligations=[
                    dict(obligation_id="waiting", operation_id="op", request_id=None, fate=fate)
                ],
                uses=[
                    dict(
                        use_id="u",
                        obligation_id="waiting",
                        request_id=None,
                        derivation_id=None,
                        selection={},
                        fate=fate,
                    )
                ],
            )
        )
        snapshot = snapshot_from_index(
            SimpleNamespace(release_id="release"),
            CutSelection(json_bytes(pins)),
            index,
            "bound-requests",
        )
        assert {node.kind for node in snapshot.nodes} == {"obligation", "use"}
        assert len(snapshot.occurrences) == 1
        assert snapshot.occurrences[0].source == 'ddo.selected-obligation:"waiting"'
        assert snapshot.occurrences[0].target == 'ops.demand_use:"u"'
        assert (
            json.loads(next(node for node in snapshot.nodes if node.kind == "use").payload_json)[
                "fate"
            ]
            == fate
        )
    finally:
        index.close()


@pytest.mark.parametrize("fate", ["attached", "fulfilled"])
def test_executable_use_cannot_omit_its_native_request(tmp_path, monkeypatch, fate):
    from corpus_structure.semantic import data_operation_admission

    monkeypatch.setattr(
        data_operation_admission,
        "bound_data_operation_model",
        lambda prepared: model(operation("operation")),
    )
    index, cut = selected_index(tmp_path)
    try:
        index.append_page(
            dict(
                **cut.record,
                obligations=[],
                uses=[
                    dict(
                        use_id="invalid",
                        obligation_id="invalid",
                        request_id=None,
                        derivation_id=None,
                        selection={},
                        fate=fate,
                    )
                ],
            )
        )
        with pytest.raises(ValueError, match="attached or fulfilled use lacks"):
            snapshot_from_index(SimpleNamespace(release_id="release"), cut, index, "bound-requests")
    finally:
        index.close()


@pytest.mark.parametrize("projection", ["bound-requests", "selected-support"])
def test_native_authority_is_an_explicit_unknown_boundary(tmp_path, monkeypatch, projection):
    from corpus_structure.semantic import data_operation_admission

    monkeypatch.setattr(
        data_operation_admission,
        "bound_data_operation_model",
        lambda prepared: model(operation("operation")),
    )
    index, cut = selected_index(tmp_path)
    # This is a controlled transferred graph, not native admission evidence.
    index.connection.exec_driver_sql(
        "DELETE FROM records WHERE relation='ops.demand_use' AND json_extract(payload,'$.record.id')='su'"
    )
    index.connection.exec_driver_sql(
        "DELETE FROM records WHERE relation='ops.data_derivation' AND json_extract(payload,'$.record.id') IN ('new','old')"
    )
    index.connection.exec_driver_sql(
        "DELETE FROM records WHERE relation='ops.data_request' AND json_extract(payload,'$.record.id')='producer'"
    )
    leaf = dict(
        format="ddo-native-authority-leaf-v1",
        derivation_id="new",
        use_id="su",
        issuer_operation="record_policy.authorize",
        release_id="issuer-release",
        runtime_id="issuer-runtime",
        recipe="issuer-recipe",
        product_id="authorization",
        kind_contract="authorization-kind",
        intent_id="opaque-intent",
        receipt_id="opaque-receipt",
        standing="valid",
        protected_dependencies="undisclosed",
    )
    for relation, row in (
        ("ops.data_authority_leaf", leaf),
        ("kb.data_product", dict(id="authorization")),
    ):
        index.append(json_bytes(dict(key=relation + ":controlled", relation=relation, record=row)))
    try:
        snapshot = snapshot_from_index(
            SimpleNamespace(release_id="release"), cut, index, projection
        )
        assert snapshot.standing == "partial"
        assert any(
            "protected dependencies" in reason and "undisclosed" in reason
            for reason in snapshot.unknowns
        )
        assert any(node.kind == "authority" for node in snapshot.nodes)
        boundary = 'ops.data_authority_leaf:["new","su"]'
        assert any(
            edge.source == 'ops.demand_use:"cu"' and edge.target == boundary
            for edge in snapshot.occurrences
        )
        assert not any(
            node.identity
            in {'ops.demand_use:"su"', 'ops.data_derivation:"new"', 'ops.data_request:"producer"'}
            for node in snapshot.nodes
        )
    finally:
        index.close()
