"""Exact COPY values have no caller-controlled attempt or rule evidence fields."""

import struct
from dataclasses import replace

import pyarrow as pa
import pytest
from sqlalchemy import Boolean, Column, MetaData, Table, Text

from corpus_structure.schema.physical import compile_physical, physical_source_closure
from corpus_structure.semantic.arrow_transfer import ArrowTransferError
from corpus_structure.semantic.metadata import PHYSICAL_MODEL
from corpus_structure.semantic.population_transfer import population_item_write_profile


@pytest.fixture(scope="module")
def physical_model():
    sources = physical_source_closure(
        PHYSICAL_MODEL.name, lambda name: PHYSICAL_MODEL.with_name(name).read_bytes()
    )
    return compile_physical(sources)


def test_population_copy_uses_exact_canonical_item_text_and_fresh_encoders(physical_model):
    profile = population_item_write_profile(release_id="release:one", model=physical_model)
    assert profile.schema.names == [
        "output_role",
        "output_position",
        "collection",
        "partition_key",
        "item_ordinal",
        "canonical_text",
    ]
    assert all(not field.nullable for field in profile.schema)
    assert [field.wire_type for field in profile.fields] == [
        "text",
        "bigint",
        "text",
        "text",
        "bigint",
        "text",
    ]
    text = '["mapping",[["label",["string","é"]],["value",["integer","123456789012345678901234567890"]]]]'
    batch = pa.RecordBatch.from_arrays(
        [
            pa.array(["reports"]),
            pa.array([0], type=pa.int64()),
            pa.array(["rows"]),
            pa.array(["block:one"]),
            pa.array([7], type=pa.int64()),
            pa.array([text]),
        ],
        schema=profile.schema,
    )
    expected = [
        b"reports",
        struct.pack("!q", 0),
        b"rows",
        b"block:one",
        struct.pack("!q", 7),
        text.encode(),
    ]
    for _ in range(2):
        encoder = profile.new_encoder()
        profile.validate_batch(batch)
        encoded = encoder.write_header() + encoder.write_batch(batch) + encoder.finish()
        assert encoded[:19] == b"PGCOPY\n\xff\r\n\0" + b"\0" * 8
        offset = 19
        assert struct.unpack_from("!h", encoded, offset)[0] == 6
        offset += 2
        for value in expected:
            length = struct.unpack_from("!i", encoded, offset)[0]
            offset += 4
            assert encoded[offset : offset + length] == value
            offset += length
        assert encoded[offset:] == struct.pack("!h", -1)
    assert profile.schema.metadata[b"source_relation"] == b"ops.data_retained_population_item"
    assert profile.schema.metadata[b"release_id"] == b"release:one"


def test_population_copy_rejects_extra_fields_and_changed_wire_contract(physical_model):
    profile = population_item_write_profile(release_id="release:one", model=physical_model)
    empty = pa.RecordBatch.from_arrays(
        [pa.array([], type=field.type) for field in profile.schema], schema=profile.schema
    )
    for changed in (
        empty.select([1, 0, 2, 3, 4, 5]),
        empty.replace_schema_metadata(None),
        empty.append_column("intent_id", pa.array([], type=pa.string())),
        empty.append_column("address_key", pa.array([], type=pa.string())),
    ):
        with pytest.raises(ArrowTransferError, match="wire schema"):
            profile.validate_batch(changed)
    changed_release = population_item_write_profile(release_id="release:two", model=physical_model)
    assert changed_release.identity != profile.identity
    assert replace(profile, physical_id="other").identity != profile.identity


def test_population_upload_derivation_refuses_an_unsupported_physical_field():
    model = MetaData(info={"physical_model_id": "test:physical"})
    Table(
        "data_retained_population_item",
        model,
        Column("output_role", Boolean(), nullable=False),
        Column("output_position", Text(), nullable=False),
        Column("collection", Text(), nullable=False),
        Column("partition_key", Text(), nullable=False),
        Column("item_ordinal", Text(), nullable=False),
        Column("canonical_text", Text(), nullable=False),
        schema="ops",
    )
    with pytest.raises(ValueError, match="unsupported population upload field"):
        population_item_write_profile(release_id="release:one", model=model)
