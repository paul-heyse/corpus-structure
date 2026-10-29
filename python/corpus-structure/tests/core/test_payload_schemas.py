"""Reader dispatch by recorded payload schema (P0-M-4): typed refusal of an unknown id, upcasts."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from corpus_structure.core import payloads
from corpus_structure.core.payload_schemas import (
    PayloadReaders,
    PayloadSchemaRow,
    UnknownPayloadKind,
    UnknownPayloadSchema,
    UnknownUpcaster,
)
from corpus_structure.schema import model, registry

MENTION = {"label": "RandomVariable", "text": "X", "start": 0, "end": 1}
ROWS = [
    PayloadSchemaRow(11, "sys:MentionPayload", "mention", 1, None, None),
    PayloadSchemaRow(12, "sys:MentionPayload", "mention", 2, 11, "absent"),
    PayloadSchemaRow(21, "sys:TaskCost", "task_cost", 1, None, None),
]


def test_a_payload_is_read_under_its_recorded_schema() -> None:
    readers = PayloadReaders(ROWS)
    read = readers.read(11, MENTION)
    assert isinstance(read, payloads.MentionPayload) and read.text == "X"
    assert readers.upcast(11, MENTION)[0].version == 2  # upcast along the class's versions
    assert readers.read(12, MENTION) == read
    assert readers.read(21, {"wall_ms": 3}).wall_ms == 3
    with pytest.raises(ValidationError):
        readers.read(11, {"label": "x"})


def test_an_unknown_payload_schema_id_is_refused() -> None:
    with pytest.raises(UnknownPayloadSchema, match="payload schema 99 is not registered") as err:
        PayloadReaders(ROWS).read(99, MENTION)
    assert err.value.payload_schema_id == 99
    assert isinstance(err.value, LookupError)


def test_an_upcaster_or_kind_without_code_is_refused() -> None:
    rows = [*ROWS[:1], PayloadSchemaRow(12, "sys:MentionPayload", "mention", 2, 11, "split_text")]
    with pytest.raises(UnknownUpcaster, match="split_text"):
        PayloadReaders(rows).read(11, MENTION)
    with pytest.raises(UnknownPayloadKind, match="'gossip'"):
        PayloadReaders([PayloadSchemaRow(1, "sys:X", "gossip", 1, None, None)]).read(1, {})


def test_every_registered_kind_has_a_reader() -> None:
    entries = registry.payload_schema_entries(model.load())
    rows = [
        PayloadSchemaRow(i, e.class_, e.kind, e.version, None, e.upcaster)
        for i, e in enumerate(entries, 1)
    ]
    readers = PayloadReaders(rows)
    assert {e.kind for e in entries} <= set(readers.readers)
