"""Boundary checks for immutable inventory binding and pre-hydration admission."""

import base64
import json

import pytest

from corpus_structure.semantic.query import ReadLimit, ReadSession, SnapshotBinding
from corpus_structure.semantic.refusals import WrongBinding


class Result:
    def __init__(self, rows):
        self.rows = rows

    def scalar_one_or_none(self):
        return "fact"

    def mappings(self):
        return self

    def all(self):
        return self.rows


class Connection:
    def __init__(self, *, scalar_bytes=100):
        self.calls = []
        self.scalar_bytes = scalar_bytes

    def execute(self, stmt):
        self.calls.append(stmt)
        keys = set(stmt.selected_columns.keys())
        if keys == {"fact_id"}:
            return Result([])
        if "scalar_bytes" in keys:
            assert stmt._limit_clause.value == 2
            return Result(
                [
                    dict(inventory_identity="o1", scalar_bytes=self.scalar_bytes),
                    dict(inventory_identity="o2", scalar_bytes=self.scalar_bytes),
                ]
            )
        assert stmt._limit_clause.value == 1
        return Result(
            [
                dict(
                    occurrence_id="o1",
                    fact_id="fact",
                    source="source",
                    item="1",
                    report_object_value_id="v",
                    report_qualification_value_id=None,
                )
            ]
        )


def session(conn):
    result = object.__new__(ReadSession)
    object.__setattr__(result, "connection", conn)
    object.__setattr__(result, "binding", SnapshotBinding("release", "realization", 1, "capture"))
    return result


def test_inventory_limits_metadata_before_hydration_and_binds_its_cursor():
    conn = Connection()
    reader = session(conn)
    page = reader.inventory("fact", "supports", limit=1, max_bytes=4096)
    assert page.items[0]["occurrence_id"] == "o1"
    assert page.population_complete is False
    assert page.next_page_token
    assert len(conn.calls) == 3
    assert "payload" not in str(conn.calls[1])
    with pytest.raises(WrongBinding):
        reader.inventory(
            "other", "supports", continuation=page.next_page_token, limit=1, max_bytes=4096
        )
    # JSON booleans must not compare as integer revisions.
    body = json.loads(base64.urlsafe_b64decode(page.next_page_token))
    body["revision"] = True
    token = base64.urlsafe_b64encode(json.dumps(body).encode()).decode()
    with pytest.raises(WrongBinding):
        reader.inventory("fact", "supports", continuation=token, limit=1, max_bytes=4096)


def test_oversized_inventory_metadata_refuses_before_body_hydration():
    conn = Connection(scalar_bytes=8192)
    with pytest.raises(ReadLimit) as caught:
        session(conn).inventory("fact", "supports", limit=1, max_bytes=4096)
    assert caught.value.reason == "oversized_item"
    assert len(conn.calls) == 2


class GraphConnection:
    def __init__(self, *, node_bytes=100, role=None):
        self.calls = []
        self.node_bytes, self.role = node_bytes, role

    def execute(self, stmt):
        self.calls.append(stmt)
        keys = set(stmt.selected_columns.keys())
        if keys == {"value_id", "bytes"}:
            assert stmt._limit_clause.value <= 64
            return Result([dict(value_id="root", bytes=self.node_bytes)])
        if keys == {"parent_value_id", "role", "position", "child_value_id", "bytes"}:
            assert stmt._limit_clause.value <= 64
            return Result(
                [
                    dict(
                        parent_value_id="root",
                        role=self.role,
                        position=0,
                        child_value_id="child",
                        bytes=100,
                    )
                ]
            )
        raise AssertionError("value bodies must not be hydrated after graph admission refuses")


def test_oversized_graph_and_unbounded_role_key_refuse_before_value_bodies():
    conn = GraphConnection(node_bytes=8 * 1024 * 1024 + 1)
    with pytest.raises(ReadLimit) as caught:
        session(conn)._values({"root"}, set())
    assert caught.value.reason == "work_limit" and len(conn.calls) == 1
    conn = GraphConnection(role=None)
    with pytest.raises(ReadLimit):
        session(conn)._values({"root"}, set())
    assert len(conn.calls) == 2


def test_label_lookup_uses_released_display_role_and_property_case_policy():
    from types import SimpleNamespace

    from corpus_structure.serve.read import Reader

    binding = SnapshotBinding("release", "realization", 1, "capture")
    prepared = SimpleNamespace(
        definitions=[SimpleNamespace(iri="class:custom")],
        display_properties=lambda iri: (
            SimpleNamespace(iri="property:custom-display", case_policy="casefold"),
        ),
    )
    owned = SimpleNamespace(binding=binding, prepared=prepared)
    reader = Reader(SimpleNamespace(session=owned, conn=None))
    stmt = reader.entity_ids(label="Straße")
    params = stmt.compile().params
    assert "property:custom-display" in params.values()
    assert "strasse" in params.values()
    assert "casefold" in str(stmt)
    assert "canonical_name" not in str(stmt)
