"""Independent value/presence and actual IPC contract cases for page payloads."""

import json
import math
from copy import deepcopy
from decimal import Decimal
from hashlib import sha256

import pyarrow as pa
import pytest
from jsonschema.exceptions import ValidationError

from corpus_structure.semantic.pdf_payloads import (
    PayloadContractError,
    PreparedPayloadFamily,
    decode_page_payload,
    encode_page_payload,
    page_payload_batches,
    prepare_payload_family,
    prepare_payload_schema,
    prepare_schema_validator,
    schema_dump,
    schema_load,
)

from .test_pdf_ocr_contracts import inventory


@pytest.fixture(scope="module")
def family():
    return prepare_payload_family()


def test_nested_page_roundtrip_preserves_values_presence_and_numeric_kinds(family):
    page = inventory()
    page["candidates"][0]["before"] = "NUL\x00 context"
    page["candidates"][0]["left"] = -0.0
    page["candidates"][0]["right"] = 12
    payload = family.encode(page)
    actual = family.decode(
        payload, schema_digest=family.schema_digest, logical_digest=family.logical_digest(page)
    )
    assert actual == page
    assert type(actual["candidates"][0]["right"]) is int
    assert type(actual["candidates"][0]["left"]) is float
    assert math.copysign(1, actual["candidates"][0]["left"]) == -1
    assert "font" not in actual["candidates"][0]
    assert actual["candidates"][0]["before"] == "NUL\x00 context"
    assert pa.types.is_struct(family.arrow_schema.field("ocr_regions").type.value_type)


def test_compression_changes_bytes_not_logical_meaning(family):
    page = inventory()
    plain, compressed = family.encode(page), family.encode(page, compression="zstd")
    assert plain != compressed
    assert family.logical_digest(family.decode(plain)) == family.logical_digest(
        family.decode(compressed)
    )
    changed = deepcopy(page)
    changed["has_vectors"] = False
    assert family.logical_digest(changed) != family.logical_digest(page)
    # Independent canonical input ensures numeric tags/presence are meaning-bearing,
    # while actual IPC compression and framing are excluded from logical identity.
    expected = sha256(
        b"pdf-page-logical-v1\0"
        + family.schema_digest.encode()
        + b"\0"
        + json.dumps(page, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
    assert family.logical_digest(page) == expected
    family.read_batch(compressed, logical_digest=expected).validate(full=True)


def test_absent_empty_and_explicit_defaults_are_distinct(family):
    absent = dict(page_no=1, has_words=False, has_chars=False)
    empty = {**absent, "ocr_regions": [], "candidates": []}
    default = {**absent, "has_vectors": False}
    assert family.decode(family.encode(absent)) == absent
    assert family.decode(family.encode(empty)) == empty
    assert family.decode(family.encode(default)) == default
    assert len({family.logical_digest(x) for x in (absent, empty, default)}) == 3
    with pytest.raises(PayloadContractError):
        family.encode({**absent, "ocr_regions": None})


@pytest.mark.parametrize(
    "change",
    [
        {"page_no": True},
        {"page_no": 1.0},
        {"page_no": 2**70},
        {"unexpected": 1},
        {"has_chars": None},
    ],
)
def test_invalid_source_values_refuse_without_coercion(family, change):
    page = dict(page_no=1, has_words=False, has_chars=False)
    with pytest.raises(PayloadContractError):
        family.encode({**page, **change})


def test_mismatched_schema_digest_and_logical_value_refuse(family):
    page = inventory()
    encoded = family.encode(page)
    with pytest.raises(PayloadContractError, match="schema binding"):
        family.decode(encoded, schema_digest="0" * 64)
    with pytest.raises(PayloadContractError, match="logical digest"):
        family.decode(encoded, logical_digest="0" * 64)
    with pytest.raises(PayloadContractError, match="trailing"):
        family.decode(encoded + b"ignored")
    schema = dict(family.json_schema)
    schema["properties"] = {**schema["properties"], "new_field": {"type": "string"}}
    other = prepare_payload_schema(schema)
    assert other.schema_digest != family.schema_digest
    with pytest.raises(PayloadContractError, match="IPC schema"):
        other.decode(encoded)


def test_empty_and_multiple_pages_refuse(family):
    for count in (0, 2):
        sink = pa.BufferOutputStream()
        with pa.ipc.new_stream(sink, family.arrow_schema) as writer:
            for _ in range(count):
                writer.write_batch(family.batch(inventory()))
        with pytest.raises(PayloadContractError, match="exactly one"):
            family.decode(sink.getvalue().to_pybytes())


def test_public_helpers_and_detached_batches():
    page = inventory()
    encoded = encode_page_payload(page)
    assert encoded.page_no == 1
    assert (
        decode_page_payload(
            encoded.content,
            schema_digest=encoded.schema_digest,
            logical_digest=encoded.logical_digest,
        )
        == page
    )
    batches = list(page_payload_batches(encoded.content, columns=["page_no", "ocr_regions"]))
    assert batches[0].schema.names == ["page_no", "ocr_regions"]
    assert batches[0].column(0).to_pylist() == [1]


def test_arrow_reader_does_not_reconstruct_page_mapping(family, monkeypatch):
    page = inventory()
    page["candidates"][0]["left"] = -0.0
    content = family.encode(page)
    digest = family.logical_digest(page)

    def refuse_mapping(*args, **kwargs):
        raise AssertionError("mapping hydration is not the Arrow reader route")

    monkeypatch.setattr(PreparedPayloadFamily, "decode", refuse_mapping)
    monkeypatch.setattr(PreparedPayloadFamily, "batch", refuse_mapping)
    batches = list(page_payload_batches(content, logical_digest=digest, columns=["candidates"]))
    assert batches[0].num_rows == 1
    assert batches[0].column(0).offsets.to_pylist() == [0, 1]


def test_arrow_physical_validity_does_not_replace_requiredness(family):
    page = inventory()
    row = family.batch(page).to_pylist()[0]
    row["page_no"] = None
    batch = pa.RecordBatch.from_pylist([row], schema=family.arrow_schema)
    batch.validate(full=True)
    sink = pa.BufferOutputStream()
    with pa.ipc.new_stream(sink, family.arrow_schema) as writer:
        writer.write_batch(batch)
    with pytest.raises(PayloadContractError):
        family.decode(sink.getvalue().to_pybytes())


def test_admitted_projection_reads_only_selected_columns_without_logical_rescan(
    family, monkeypatch
):
    import corpus_structure.semantic.pdf_payloads as payloads

    content = family.encode(inventory(), compression="zstd")

    def refuse_logical_rescan(*args, **kwargs):
        raise AssertionError("admitted projection must not walk unrelated logical page values")

    monkeypatch.setattr(payloads, "_canonical_scalar", refuse_logical_rescan)
    batch = family.read_batch(
        content, schema_digest=family.schema_digest, columns=("page_no", "candidates")
    )
    assert batch.schema.names == ["page_no", "candidates"]
    assert batch.column("page_no")[0].as_py() == 1
    assert batch.column("candidates")[0].values.field("basis")[0].as_py() == "ocr-word-token-v1"
    with pytest.raises(PayloadContractError, match="whole-page logical identity"):
        family.read_batch(content, columns=("page_no",), logical_digest="0" * 64)
    with pytest.raises(PayloadContractError, match="schema/profile"):
        other = PreparedPayloadFamily(
            family.json_schema,
            family.arrow_schema.with_metadata({"other": "profile"}),
            family.schema_digest,
            family.validator,
        )
        other.read_batch(content, columns=("page_no",))


def test_schema_capture_preserves_exact_decimal_constraints():
    schema = {"type": "number", "minimum": Decimal("1.0000000000000000001")}
    restored = schema_load(schema_dump(schema))
    assert restored == schema
    assert type(restored["minimum"]) is Decimal
    validator = prepare_schema_validator(restored)
    assert validator is prepare_schema_validator(schema)
    validator.validate(2)
    with pytest.raises(ValidationError):
        # A float conversion would round the minimum to 1 and accept this input.
        validator.validate(1)


@pytest.mark.parametrize("contradiction", ["presence", "numeric_kind"])
def test_logical_reader_rejects_contradictory_physical_tags(family, contradiction):
    row = family.batch(inventory()).to_pylist()[0]
    if contradiction == "presence":
        row["__present"] = b"\x00"
    else:
        row["candidates"][0]["left"] = {"kind": 1, "integer": 4, "binary64": 4.0}
    batch = pa.RecordBatch.from_pylist([row], schema=family.arrow_schema)
    batch.validate(full=True)
    sink = pa.BufferOutputStream()
    with pa.ipc.new_stream(sink, family.arrow_schema) as writer:
        writer.write_batch(batch)
    with pytest.raises(PayloadContractError):
        family.decode(sink.getvalue().to_pybytes())
