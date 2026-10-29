"""The repository (P0-F-4): renditions, spans, observations, payload schema ids and dispatch."""

from __future__ import annotations

from types import SimpleNamespace

import pytest
from sqlalchemy import Connection, func, select, text
from sqlalchemy.exc import IntegrityError

from corpus_structure.core import db as store
from corpus_structure.core.db import repo
from corpus_structure.core.evidence import RenditionContent, Segment
from corpus_structure.core.payload_schemas import UnknownPayloadSchema
from corpus_structure.core.payloads import MentionPayload

T = store.metadata.tables
TEXT = "Suppose X is normal. Then Y is too."


def content(text_: str = TEXT) -> RenditionContent:
    sentence1 = Segment(kind="sentence", start=0, end=20)
    sentence2 = Segment(kind="sentence", start=21, end=len(text_))
    paragraph = Segment(kind="paragraph", start=0, end=len(text_), children=(sentence1, sentence2))
    unit = Segment(kind="unit", start=0, end=len(text_), attrs={"id": "u1"}, children=(paragraph,))
    return RenditionContent(
        canonical_text=text_,
        document=Segment(kind="document", start=0, end=len(text_), children=(unit,)),
    )


def build(w: SimpleNamespace, config: int | None = None) -> repo.Build:
    return repo.Build(config or w.config, w.task, w.payload["parse_detail"], {"warnings": []})


def count(db: Connection, table: str) -> int:
    return int(db.execute(select(func.count()).select_from(T[table])).scalar_one())


def test_identical_content_is_one_rendition_with_one_set_of_segments(
    db: Connection, world: SimpleNamespace
) -> None:
    first = repo.store_rendition(db, world.document, world.document_key, content(), build(world))
    again = repo.store_rendition(db, world.document, world.document_key, content(), build(world))
    other = repo.store_rendition(
        db, world.document, world.document_key, content(), build(world, world.config2)
    )
    assert first.created and not again.created and not other.created
    assert first.id == again.id == other.id
    assert count(db, "kb.rendition") == 1
    assert count(db, "kb.segment") == 5  # document, unit, paragraph, two sentences: written once
    assert count(db, "kb.rendition_build") == 2  # one build per configuration
    rows = db.execute(
        text(
            "SELECT kind, parent_id IS NULL, depth, ordinal, text, ts_config::text "
            "FROM kb.segment ORDER BY start_offset, end_offset DESC, depth"
        )
    ).all()
    assert rows[0] == ("document", True, 0, 0, TEXT, "english")
    assert [r[0] for r in rows] == ["document", "unit", "paragraph", "sentence", "sentence"]
    assert rows[-1][4] == "Then Y is too." and rows[-1][3] == 1


def test_a_build_naming_another_rendition_is_refused(
    db: Connection, world: SimpleNamespace
) -> None:
    repo.store_rendition(db, world.document, world.document_key, content(), build(world))
    with pytest.raises(repo.NondeterministicIngest, match="not deterministic"):
        repo.store_rendition(
            db, world.document, world.document_key, content(TEXT + " Done."), build(world)
        )


def test_span_upsert_returns_the_same_ids_and_refuses_out_of_text(
    db: Connection, world: SimpleNamespace
) -> None:
    ren = repo.store_rendition(db, world.document, world.document_key, content(), build(world))
    ranges = [(8, 9), (26, 27), (0, 20)]
    ids = repo.upsert_spans(db, ren.id, ranges)
    assert repo.upsert_spans(db, ren.id, list(reversed(ranges))) == list(reversed(ids))
    spans = db.execute(
        text(
            "SELECT s.text, g.kind FROM kb.span s JOIN kb.segment g "
            "ON g.id = s.segment_id ORDER BY s.id"
        )
    ).all()
    assert spans == [("X", "sentence"), ("Y", "sentence"), ("Suppose X is normal.", "sentence")]
    for bad in ([(30, 99)], [(5, 5)], [(-1, 2)]):
        with pytest.raises(repo.SpanOutOfText):
            repo.upsert_spans(db, ren.id, bad)
    assert count(db, "kb.span") == 3


def mention(ordinal: int) -> repo.ObservationRow:
    payload = MentionPayload.model_validate(
        {"label": "RandomVariable", "text": "X", "start": 8, "end": 9}
    )
    return repo.ObservationRow(ordinal, "mention", payload)


def test_observations_carry_the_registered_payload_schema(
    db: Connection, world: SimpleNamespace
) -> None:
    assert repo.write_observations(db, world.task, 0, [mention(0), mention(1)]) == 2
    rows = db.execute(text("SELECT payload_schema_id, payload FROM kb.observation")).all()
    assert {r[0] for r in rows} == {world.payload["mention"]}
    assert rows[0][1] == {"label": "RandomVariable", "text": "X", "start": 8, "end": 9}
    readers = repo.payload_readers(db)
    read = repo.read_payload(readers, rows[0][0], rows[0][1])
    assert isinstance(read, MentionPayload) and read.text == "X"
    with pytest.raises(UnknownPayloadSchema):
        repo.read_payload(readers, 10**9, rows[0][1])


def test_an_unregistered_kind_is_refused_before_any_write(
    db: Connection, world: SimpleNamespace
) -> None:
    db.execute(text("DELETE FROM meta.payload_schema WHERE kind = 'mention'"))
    with pytest.raises(repo.UnregisteredPayload, match="mention"):
        repo.write_observations(db, world.task, 0, [mention(0)])
    assert count(db, "kb.observation") == 0


def test_a_payload_row_with_an_unregistered_schema_id_is_refused(
    db: Connection, world: SimpleNamespace
) -> None:
    refused = pytest.raises(IntegrityError, match="fk_observation_payload_schema_id")
    with refused, db.begin_nested():
        db.execute(
            text(
                "INSERT INTO kb.observation (task_id, ordinal, kind, payload, "
                "payload_schema_id, outcome) VALUES (:t, 0, 'mention', '{}', 999999999, "
                "'produced')"
            ),
            {"t": world.task},
        )


def test_get_or_create_reports_new_rows(db: Connection, world: SimpleNamespace) -> None:
    method = T["ops.method"]
    values = {"name": "extract.gliner", "version": "2", "family": "extract"}
    first = repo.get_or_create(db, method, values, ["name", "version"])
    assert first[1] is True
    assert repo.get_or_create(db, method, values, ["name", "version"]) == (first[0], False)


def test_bulk_primitives(db: Connection, world: SimpleNamespace) -> None:
    ids = repo.allocate_ids(db, T["ops.task"], 3)
    assert ids == sorted(ids) and len(set(ids)) == 3
    made = repo.insert_returning(
        db,
        T["ops.method"],
        [
            {"name": "a", "version": "1", "family": "ingest"},
            {"name": "b", "version": "1", "family": "ingest"},
        ],
    )
    names = (
        db.execute(text("SELECT name FROM ops.method WHERE id = ANY(:i) ORDER BY id"), {"i": made})
        .scalars()
        .all()
    )
    assert names == ["a", "b"]
