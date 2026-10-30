"""Independent old boundary vectors against a genuine pre-change compiler-10 archive."""

from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path

import pytest
from pydantic import ValidationError

from corpus_structure.semantic.archive_reader import reconstruct_release
from corpus_structure.semantic.types import (
    PreparationProfile,
    PreparedArtifact,
    SourceArtifact,
    SourceBundle,
)

_FIXTURE = Path(__file__).parents[1] / "fixtures/semantic/reader-v10.json"


def archived(path: Path = _FIXTURE):
    data = json.loads(path.read_bytes())
    bundle = SourceBundle(
        data["root"],
        tuple(
            SourceArtifact(item["name"], bytes.fromhex(item["content"])) for item in data["sources"]
        ),
    )
    artifacts = tuple(
        PreparedArtifact(item["kind"], bytes.fromhex(item["content"])) for item in data["artifacts"]
    )
    return data, bundle, artifacts


def test_v10_archive_uses_products_without_current_preparation(monkeypatch):
    import corpus_structure.semantic.prepare as compiler

    def unavailable(*args, **kwargs):
        raise AssertionError("current preparation is not a read dependency")

    monkeypatch.setattr(compiler, "prepare_release", unavailable)
    data, bundle, artifacts = archived()
    prepared = reconstruct_release(
        data["products"],
        bytes.fromhex(data["manifest"]),
        bundle,
        PreparationProfile(**data["profile"]),
        artifacts,
    )
    assert (
        prepared.release_id
        == "release:948013893dd34047c01e9ee7f423942b4d3e6768f168099e4de5893c44518a8a"
    )
    value = prepared.validate_json(
        "Record",
        """{"id":"r","values":{"a":{"id":"a","kind":"Circle","exact_amount":"1.2300"}},"shape":{"id":"b","kind":"Circle","exact_amount":"2"}}""",
    )
    fields = value.model_dump()
    assert str(fields["values"]["a"]["amount"]) == "1.2300"
    assert fields["shape"]["kind"] == "Circle"
    with pytest.raises(ValidationError):
        prepared.validate_json("Circle", '{"id":"a","kind":"Circle","exact_amount":"-1"}')
    with pytest.raises(ValidationError):
        prepared.validate_json("Circle", '{"id":"a","kind":"Circle","typo":"1"}')
    with pytest.raises(ValidationError):
        prepared.validate_json("Record", '{"id":"r","values":{"wrong":{"id":"a","kind":"Circle"}}}')


@pytest.mark.parametrize(
    "corruption", ["schema", "artifact", "unknown_product", "unknown_compiler"]
)
def test_archive_boundary_corruption_or_unknown_abi_refuses(corruption):
    data, bundle, artifacts = archived()
    products = deepcopy(data["products"])
    profile = PreparationProfile(**data["profile"])
    if corruption == "unknown_product":
        products["future_meaning"] = True
    elif corruption == "unknown_compiler":
        profile = PreparationProfile(compiler_version="999")
    else:
        kind = "json_schema/Record" if corruption == "schema" else "definitions.json"
        artifacts = tuple(
            PreparedArtifact(item.kind, b"{}") if item.kind == kind else item for item in artifacts
        )
        if corruption == "schema":
            for item in products["artifacts"]:
                if item["kind"] == kind:
                    item["digest"] = next(a.digest for a in artifacts if a.kind == kind)
    with pytest.raises((ValueError, KeyError)):
        reconstruct_release(products, bytes.fromhex(data["manifest"]), bundle, profile, artifacts)


def test_current_boundary_recipe_opens_without_full_preparation():
    from corpus_structure.semantic.identity import canonical_bytes
    from corpus_structure.semantic.prepare import prepare_release
    from corpus_structure.semantic.releases import _products

    _data, bundle, _ = archived()
    current = prepare_release(bundle)
    opened = reconstruct_release(
        json.loads(canonical_bytes(_products(current))),
        current.manifest,
        bundle,
        PreparationProfile(),
        current.artifacts,
    )
    assert opened.release_id == current.release_id
    assert (
        opened.validate_json(
            "Circle", '{"id":"a","kind":"Circle","exact_amount":"1.200"}'
        ).model_dump()
        == current.validate_json(
            "Circle", '{"id":"a","kind":"Circle","exact_amount":"1.200"}'
        ).model_dump()
    )


def test_compiler10_public_snapshot_reads_survive_unavailable_current_compiler(
    semantic_db_engine, semantic_writer_engine, semantic_reader_engine, monkeypatch, tmp_path
):
    from decimal import Decimal

    from sqlalchemy import insert

    from corpus_structure.semantic.identity import fact_key
    from corpus_structure.semantic.metadata import table
    from corpus_structure.semantic.publication import (
        EntityRow,
        EvidenceRow,
        FactRow,
        MembershipRow,
        MembershipSupportRow,
        PublicationBatch,
        SelectionRow,
        ValueRow,
        publish_batch,
    )
    from corpus_structure.semantic.query import QuerySpec, read_session
    from corpus_structure.semantic.releases import persist_release
    from corpus_structure.semantic.types import ResolvedDependencies

    data, bundle, artifacts = archived(_FIXTURE.with_name("reader-v10-analytics.json"))
    profile = PreparationProfile(**data["profile"])
    prepared = reconstruct_release(
        data["products"], bytes.fromhex(data["manifest"]), bundle, profile, artifacts
    )
    r, z = prepared.release_id, "realization:v10-reader"
    dependencies = ResolvedDependencies(
        tuple(
            SourceArtifact(item["name"], bytes.fromhex(item["content"]))
            for item in data["dependencies"]
        )
    )
    with semantic_db_engine.begin() as conn:
        persist_release(conn, bundle, dependencies, profile, prepared)
        conn.execute(insert(table("data.project")).values(project_id="v10-reader"))
        conn.execute(
            insert(table("data.realization")).values(
                realization_id=z, release_id=r, project_id="v10-reader"
            )
        )
    facts = tuple(
        FactRow(
            fact_key(r, z, "circle", "https://example.org/" + name, value, {}),
            "circle",
            "https://example.org/" + name,
            value_id,
        )
        for name, value, value_id in (
            ("id", "circle", "id"),
            ("kind", "Circle", "kind"),
            ("amount", Decimal("1.2300"), "amount"),
        )
    )
    publish_batch(
        semantic_writer_engine,
        PublicationBatch(
            r,
            z,
            "old-answer",
            entity=(EntityRow("circle"),),
            membership=(MembershipRow("circle", "https://example.org/Circle", "stated"),),
            typed_value=(
                ValueRow("id", "string", text_value="circle"),
                ValueRow("kind", "string", text_value="Circle"),
                ValueRow("amount", "decimal", decimal_lexical="1.2300"),
            ),
            fact=facts,
            selection=tuple(SelectionRow(item.fact_id) for item in facts),
            evidence=(EvidenceRow("ev", "urn:source", "line:1", "test", "1"),),
            membership_support=(
                MembershipSupportRow("circle", "https://example.org/Circle", "ev"),
            ),
        ),
    )
    import corpus_structure.semantic.prepare as compiler

    def unavailable(*args, **kwargs):
        raise AssertionError("historical public reads must not compile")

    monkeypatch.setattr(compiler, "prepare_release", unavailable)
    with read_session(semantic_reader_engine, z) as session:
        circle = session.class_handle("Circle")
        result = session.query(
            QuerySpec(circle, session.property_handle(circle, "amount"), "accepted")
        )
        assert result.binding.release_id == r
        assert len(result.values) == 1
        assert session.explain(facts[2].fact_id).fact_id == facts[2].fact_id
        from corpus_structure.semantic.analytics import load_packet

        uri = semantic_reader_engine.url.render_as_string(hide_password=False).replace(
            "postgresql+psycopg:", "postgresql:"
        )
        packet = load_packet(session, uri)
        assert (
            next(
                row
                for row in packet.to_table("typed_value").to_pylist()
                if row["value_id"] == "amount"
            )["decimal_lexical"]
            == "1.2300"
        )
    from corpus_structure.serve.export import export_packet

    exported = export_packet(packet, tmp_path / "old-answer")
    assert exported["binding"]["release_id"] == r


def test_current_open_builds_only_requested_boundary_closure():
    from corpus_structure.semantic.prepare import prepare_release
    from corpus_structure.semantic.releases import _products
    from corpus_structure.semantic.types import SourceArtifact, SourceBundle

    source = SourceBundle(
        "lazy",
        (
            SourceArtifact(
                "lazy",
                b"""id: https://example.org/lazy
name: lazy
types:
  string: {base: str, uri: xsd:string}
classes:
  Used:
    attributes:
      id: {identifier: true}
  Unrelated:
    attributes:
      id: {identifier: true}
""",
            ),
        ),
    )
    prepared = prepare_release(source)
    opened = reconstruct_release(
        _products(prepared), prepared.manifest, source, PreparationProfile(), prepared.artifacts
    )
    assert opened._boundary_models == {}
    assert opened.validate_python("Used", {"id": "a"}).model_dump()["id"] == "a"
    assert set(opened._boundary_models) == {"Used"}
    assert opened.adapter("Used") is opened.adapter("Used")
    with pytest.raises(TypeError):
        from typing import Any, cast

        cast(Any, opened.index.definitions)["Other"] = opened.definitions[0]


def test_extracted_float_item_keeps_finite_policy():
    from corpus_structure.semantic.prepare import prepare_release
    from corpus_structure.semantic.types import SourceArtifact, SourceBundle

    prepared = prepare_release(
        SourceBundle(
            "finite",
            (
                SourceArtifact(
                    "finite",
                    b"""id: https://example.org/finite
name: finite
types:
  string: {base: str, uri: xsd:string}
  float: {base: float, uri: xsd:float}
classes:
  Finite:
    attributes:
      id: {identifier: true}
      values: {range: float, multivalued: true}
""",
                ),
            ),
        )
    )
    item = prepared.property_adapter("Finite", "values", item=True)
    for value in (float("nan"), float("inf"), -float("inf")):
        with pytest.raises(ValidationError):
            item.validate_python(value, strict=True)
    assert item.validate_python(1.5, strict=True) == 1.5


@pytest.mark.parametrize("order", [("B", "A"), ("A", "B"), ("C", "B", "A")])
def test_overlapping_lazy_boundaries_keep_validated_instances_and_field_adapters(order):
    prepared = _overlapping_archive()
    c = prepared.validate_python("C", {"id": "c"})
    c_type = type(c)
    adapter = prepared.adapter("C")
    item = prepared.property_adapter("B", "children", item=True)
    for name in order:
        prepared.adapter(name)
    assert prepared.adapter("C") is adapter
    assert prepared._boundary_models["C"] is c_type
    assert prepared.property_adapter("B", "children", item=True) is item
    a = prepared.validate_python("A", {"id": "a", "b": {"id": "b", "c": c}})
    assert a.__dict__["b"].__dict__["c"] is c
    assert item.validate_python(c, strict=True) is c
    assert "Unrelated" not in prepared._boundary_models


def _overlapping_archive(*, corrupt_a=False):
    from corpus_structure.semantic.prepare import prepare_release
    from corpus_structure.semantic.releases import _products

    source = SourceBundle(
        "overlap",
        (
            SourceArtifact(
                "overlap",
                b"""id: https://example.org/overlap
name: overlap
types:
  string: {base: str, uri: xsd:string}
classes:
  C:
    attributes:
      id: {identifier: true}
  B:
    attributes:
      id: {identifier: true}
      c: {range: C, inlined: true}
      children: {range: C, inlined: true, multivalued: true, inlined_as_list: true}
  A:
    attributes:
      id: {identifier: true}
      b: {range: B, inlined: true}
  Unrelated:
    attributes:
      id: {identifier: true}
""",
            ),
        ),
    )
    current = prepare_release(source)
    products = _products(current)
    artifacts = current.artifacts
    if corrupt_a:
        artifacts = tuple(
            PreparedArtifact(item.kind, b"{}") if item.kind == "json_schema/A" else item
            for item in artifacts
        )
        for artifact in products["artifacts"]:
            if artifact["kind"] == "json_schema/A":
                artifact["digest"] = next(a.digest for a in artifacts if a.kind == "json_schema/A")
    return reconstruct_release(products, current.manifest, source, PreparationProfile(), artifacts)


def test_concurrent_overlapping_lazy_requests_share_one_registry():
    from concurrent.futures import ThreadPoolExecutor
    from threading import Barrier

    prepared = _overlapping_archive()
    barrier = Barrier(4)

    def demand(name):
        barrier.wait()
        if name == "item":
            return prepared.property_adapter("B", "children", item=True)
        return prepared.adapter(name)

    with ThreadPoolExecutor(max_workers=4) as workers:
        adapters = list(workers.map(demand, ("A", "B", "C", "item")))
    c = prepared.validate_python("C", {"id": "c"})
    assert adapters[2].validate_python(c, strict=True) is c
    assert adapters[3].validate_python(c, strict=True) is c
    a = prepared.validate_python("A", {"id": "a", "b": {"id": "b", "c": c}})
    assert a.__dict__["b"].__dict__["c"] is c
    assert "Unrelated" not in prepared._boundary_models


def test_failed_lazy_schema_check_does_not_publish_partial_models():
    prepared = _overlapping_archive(corrupt_a=True)
    c = prepared.validate_python("C", {"id": "c"})
    before = dict(prepared._boundary_models)
    with pytest.raises(ValueError, match="schema differs for A"):
        prepared.adapter("A")
    assert prepared._boundary_models == before
    assert prepared.validate_python("C", c) is c


def test_abstract_dispatch_reuses_previously_validated_concrete_instances():
    from corpus_structure.semantic.prepare import prepare_release
    from corpus_structure.semantic.releases import _products

    _, bundle, _ = archived()
    current = prepare_release(bundle)
    opened = reconstruct_release(
        _products(current), current.manifest, bundle, PreparationProfile(), current.artifacts
    )
    circle = opened.validate_json("Circle", '{"id":"c","kind":"Circle","exact_amount":"1.2300"}')
    opened.adapter("Shape")
    record = opened.validate_python("Record", {"id": "r", "shape": circle, "values": {"c": circle}})
    assert record.__dict__["shape"] is circle
    assert record.__dict__["values"]["c"] is circle


def test_recursive_lazy_boundary_is_canonical_when_outer_closure_is_requested():
    from corpus_structure.semantic.prepare import prepare_release
    from corpus_structure.semantic.releases import _products

    source = SourceBundle(
        "recursive",
        (
            SourceArtifact(
                "recursive",
                b"""id: https://example.org/recursive
name: recursive
types:
  string: {base: str, uri: xsd:string}
classes:
  Node:
    attributes:
      id: {identifier: true}
      children: {range: Node, inlined: true, multivalued: true, inlined_as_list: true}
  Envelope:
    attributes:
      id: {identifier: true}
      root: {range: Node, inlined: true}
""",
            ),
        ),
    )
    current = prepare_release(source)
    opened = reconstruct_release(
        _products(current), current.manifest, source, PreparationProfile(), current.artifacts
    )
    node = opened.validate_json("Node", '{"id":"root","children":[{"id":"leaf"}]}')
    node_type = type(node)
    item = opened.property_adapter("Node", "children", item=True)
    envelope = opened.validate_python("Envelope", {"id": "e", "root": node})
    assert envelope.__dict__["root"] is node
    assert opened._boundary_models["Node"] is node_type
    assert item.validate_python(node, strict=True) is node
