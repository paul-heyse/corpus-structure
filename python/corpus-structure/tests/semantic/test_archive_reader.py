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
                for row in packet.relations["typed_value"].to_pylist()
                if row["value_id"] == "amount"
            )["decimal_lexical"]
            == "1.2300"
        )
    from corpus_structure.serve.export import export_packet

    exported = export_packet(packet, tmp_path / "old-answer")
    assert exported["binding"]["release_id"] == r
