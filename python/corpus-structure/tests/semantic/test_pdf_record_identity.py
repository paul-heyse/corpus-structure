"""Independent scalar/record vectors and artifact custody for PDF-19 foundation."""

from __future__ import annotations

import gzip
import io
import struct
from dataclasses import replace
from decimal import Decimal
from hashlib import sha256
from pathlib import Path
from typing import cast

import pytest
from sqlalchemy import Engine, text
from sqlalchemy.exc import DBAPIError

from corpus_structure.semantic.pdf_record_identity import (
    ABSENT,
    BLOCK_BYTES,
    ArtifactPart,
    ArtifactPin,
    IdentityFold,
    LogicalIdentity,
    Scalar,
    byte_root,
    canonical_blocks,
    canonical_scalar,
    emit_parts,
    frame,
    record_frame,
    replay_artifact,
    same_part,
    scalar_payload,
)

# Hand-written payload bytes and fixed vectors from the specified framing, without
# importing production encoding. Empty bytes have zero blocks, not one empty block.
_EMPTY = "2181d801f42ee69518e7d6b92c41b10983814ba43dc95609b21f6356c5bfb430"
_TRUE = "3a3fa55f71f2bfd5b7502b0bd0911786ea4140895a671ca1a47d0bf745c36cae"
_MINUS12 = "96deef9ab46aa2c9fbed7c6cfa15a11b2e225a351ead9d5433f8c38a3c39f6c0"
_RECORD = (
    "5200000000000000a60000000000000002730000000000000009736368656d613a7631"
    "6600000000000000066e61746976656b0000000000000004726f6f74"
    "6e000000000000000770726573656e74620000000000000001"
    + _TRUE
    + "6e000000000000000576616c7565690000000000000003"
    + _MINUS12
)
_VECTORS: tuple[tuple[Scalar, bytes, bytes, str], ...] = (
    (ABSENT, b"a", b"", _EMPTY),
    (None, b"n", b"", _EMPTY),
    (False, b"b", b"\x00", "79d66ca1349f53e445a04f9912f8dc67366e52b141ac61bf30a924f681425d2d"),
    (True, b"b", b"\x01", _TRUE),
    (0, b"i", b"0", "18d521b4d5e54be14a4ea041621e12eabace424187f671c542d028734039b7fb"),
    (-12, b"i", b"-12", _MINUS12),
    (
        -0.0,
        b"f",
        b"\x80" + b"\0" * 7,
        "d0b2fc204e4e27ff02c7cdcbbc571b40021be02aed318f567b7b714d7a741a20",
    ),
    (
        Decimal("1.00"),
        b"d",
        b"0:100:-2",
        "990570b54d2305a47c27658033c5e25cd23fb7f80fa266aa5d0dc8af5f033d83",
    ),
    (
        "A\0é",
        b"s",
        b"A\x00\xc3\xa9",
        "4e888c0d2c4855c22650fd975ccba61df00ec0e623ce5e161f1a604494d3f48a",
    ),
)


@pytest.mark.parametrize(("value", "kind", "payload", "root"), _VECTORS)
def test_hand_scalar_vectors(value: Scalar, kind: bytes, payload: bytes, root: str) -> None:
    assert scalar_payload(value) == (kind, payload)
    expected = kind + len(payload).to_bytes(8, "big") + bytes.fromhex(root)
    assert canonical_scalar(value) == expected


def test_hand_record_and_fold_vector() -> None:
    assert frame(b"x", b"ab").hex() == "7800000000000000026162"
    actual = record_frame("schema:v1", "native", "root", (("present", True), ("value", -12)))
    assert actual.hex() == _RECORD
    fold = IdentityFold("records")
    fold.add(actual)
    assert fold.digest().hex() == "a59b4654f8a45609ff37a542489d34a156037c4f810d81f46711a2612f6a3f18"
    assert fold.digest() != sha256(actual).digest()


def test_exact_type_presence_decimal_and_unicode_distinctions() -> None:
    values = [
        ABSENT,
        None,
        False,
        0,
        0.0,
        -0.0,
        "",
        b"",
        Decimal("0"),
        Decimal("-0"),
        Decimal("0.0"),
        Decimal("1"),
        Decimal("1.00"),
        "é",
        "e\u0301",
    ]
    assert len({canonical_scalar(value) for value in values}) == len(values)
    for value in (float("nan"), float("inf"), Decimal("NaN"), Decimal("Infinity")):
        with pytest.raises(ValueError, match="finite"):
            canonical_scalar(value)
    with pytest.raises(TypeError, match="unsupported"):
        canonical_scalar(cast(Scalar, {}))


def test_logical_order_and_context_are_meaning_bearing() -> None:
    def identity(fields=(("value", 1),), *, release="r", source="1" * 64):
        digest = LogicalIdentity("schema:v1", release, source)
        digest.add_record("native", "stable-root", fields)
        return digest.pin()

    pin = identity()
    assert pin == identity()
    assert (
        len(
            {
                pin,
                identity((("value", 2),)),
                identity((("value", ABSENT),)),
                identity(release="r2"),
                identity(source="2" * 64),
            }
        )
        == 5
    )
    with pytest.raises(ValueError, match="source differs"):
        pin.require_context(schema_id="schema:v1", release_id="r", source_digest="2" * 64)
    digest = LogicalIdentity("schema:v1", "r", "1" * 64)
    digest.add_record("native", "b", (("value", 1),))
    with pytest.raises(ValueError, match="unique"):
        digest.add_record("native", "a", (("value", 1),))
    with pytest.raises(ValueError, match="unique"):
        digest.add_record("native", "b", (("value", 2),))
    assert record_frame("s", "f", "k", (("a", 1), ("b", 2))) != record_frame(
        "s", "f", "k", (("b", 2), ("a", 1))
    )
    with pytest.raises(ValueError, match="unique"):
        record_frame("s", "f", "k", (("a", 1), ("a", 1)))
    with pytest.raises(ValueError, match="bounded"):
        record_frame("s", "f", "k" * (BLOCK_BYTES + 1), ())


def _parts(raw: bytes, size: int) -> list[ArtifactPart]:
    return [
        ArtifactPart(
            "stream",
            i,
            offset,
            len(raw[offset : offset + size]),
            raw[offset : offset + size],
            sha256(raw[offset : offset + size]).hexdigest(),
        )
        for i, offset in enumerate(range(0, len(raw), size))
    ]


def _pin(raw: bytes) -> ArtifactPin:
    size, root = byte_root((raw,))
    return ArtifactPin("stream", "release", "1" * 64, size, sha256(raw).hexdigest(), root)


def test_rebatch_recompression_external_scalar_and_exact_replay() -> None:
    value = "a\0é" * BLOCK_BYTES
    raw = value.encode()
    pin = _pin(raw)
    for size in (1, 997, BLOCK_BYTES):
        parts = _parts(raw, size)
        assert (
            b"".join(
                replay_artifact(
                    parts,
                    pin,
                    release_id="release",
                    source_digest="1" * 64,
                    already_admitted=io.BytesIO(raw),
                )
            )
            == raw
        )
        assert byte_root(part.body for part in parts) == (len(raw), pin.byte_root)
    assert byte_root((gzip.decompress(gzip.compress(raw)),)) == byte_root((raw,))
    assert canonical_scalar(value) == pin.scalar(b"s").encode()
    assert record_frame("s", "f", "k", (("text", value),)) == record_frame(
        "s", "f", "k", (("text", pin.scalar(b"s")),)
    )
    assert tuple(emit_parts("stream", (raw[:10], raw[10:]))) == tuple(_parts(raw, BLOCK_BYTES))
    assert list(canonical_blocks((b"",))) == []
    assert (
        b"".join(replay_artifact([], _pin(b""), release_id="release", source_digest="1" * 64))
        == b""
    )


def test_artifact_retry_conflicts_and_corruption_refuse() -> None:
    raw = b"abcdefghij"
    parts, pin = _parts(raw, 3), _pin(raw)
    assert same_part(parts[0], replace(parts[0]))
    changed = replace(parts[0], body=b"xxx", sha256_digest=sha256(b"xxx").hexdigest())
    with pytest.raises(ValueError, match="conflicting"):
        same_part(parts[0], changed)
    corruptions = [
        parts[1:],
        parts[:-1],
        list(reversed(parts)),
        [parts[0], *parts],
        [replace(parts[0], offset=1), *parts[1:]],
        [replace(parts[0], body=b"xxx"), *parts[1:]],
        [changed, *parts[1:]],
        [replace(parts[0], stream_id="other"), *parts[1:]],
        [replace(parts[0], byte_length=2), *parts[1:]],
    ]
    for corrupt in corruptions:
        with pytest.raises(ValueError):
            tuple(replay_artifact(corrupt, pin, release_id="release", source_digest="1" * 64))
    for release, source in (("wrong", "1" * 64), ("release", "2" * 64)):
        with pytest.raises(ValueError, match="pin differs"):
            tuple(replay_artifact(parts, pin, release_id=release, source_digest=source))
    # Same digest/descriptor cannot replace independent direct retained-byte comparison.
    for retained in (raw[:-1], raw + b"suffix", b"xbcdefghij"):
        with pytest.raises(ValueError, match="retained bytes"):
            tuple(
                replay_artifact(
                    parts,
                    pin,
                    release_id="release",
                    source_digest="1" * 64,
                    already_admitted=io.BytesIO(retained),
                )
            )


def test_postgresql_independent_primitive_and_record_parity(semantic_db_engine: Engine) -> None:
    sql = Path(__file__).parents[2] / "src/corpus_structure/semantic/sql/pdf_record_identity.sql"
    with semantic_db_engine.begin() as conn:
        conn.exec_driver_sql(sql.read_text(), execution_options={"no_parameters": True})
        for value, kind, payload, root in _VECTORS:
            native = conn.execute(
                text("SELECT ops.pdf_identity_scalar(:kind,:payload)"),
                dict(kind=kind.decode(), payload=payload),
            ).scalar_one()
            expected = kind + len(payload).to_bytes(8, "big") + bytes.fromhex(root)
            assert native == expected == canonical_scalar(value)
        native = conn.execute(
            text("""SELECT ops.pdf_identity_record_frame('schema:v1','native',
            'root',ARRAY['present','value'],ARRAY[
            ops.pdf_identity_scalar('b',decode('01','hex')),
            ops.pdf_identity_scalar('i',convert_to((-12::bigint)::text,'UTF8'))])""")
        ).scalar_one()
        assert native.hex() == _RECORD
        native_fold = conn.execute(
            text("""SELECT ops.pdf_identity_fold_finish(ops.pdf_identity_fold_step(
                ops.pdf_identity_fold_start('records'),0,:record),1,:length)"""),
            {"record": native, "length": len(native)},
        ).scalar_one()
        assert native_fold.hex() == (
            "a59b4654f8a45609ff37a542489d34a156037c4f810d81f46711a2612f6a3f18"
        )
        assert conn.execute(text("SELECT float8send('-0'::float8)")).scalar_one() == struct.pack(
            ">d", -0.0
        )
        raw = ("\0é" * BLOCK_BYTES).encode()
        assert (
            conn.execute(text("SELECT ops.pdf_identity_byte_root(:raw)"), {"raw": raw}).scalar_one()
            == byte_root((raw,))[1]
        )
        for kind, payload in [
            ("i", b"01"),
            ("i", b"-0"),
            ("i", b"1\n"),
            ("b", b"\2"),
            ("f", struct.pack(">d", float("inf"))),
            ("s", b"\xed\xa0\x80"),
            ("s", b"\xc0\x80"),
            ("s", b"\xf4\x90\x80\x80"),
            ("d", b"0:01:-2"),
        ]:
            with pytest.raises(DBAPIError), conn.begin_nested():
                conn.execute(
                    text("SELECT ops.pdf_identity_scalar(:kind,:payload)"),
                    dict(kind=kind, payload=payload),
                )


def test_retained_correspondence_accepts_short_reads():
    class ShortReader(io.BytesIO):
        def read(self, size=-1):
            return super().read(min(size, 7) if size >= 0 else 7)

    raw = b"retained" * 100
    assert (
        b"".join(
            replay_artifact(
                _parts(raw, 64),
                _pin(raw),
                release_id="release",
                source_digest="1" * 64,
                already_admitted=ShortReader(raw),
            )
        )
        == raw
    )
    with pytest.raises(ValueError, match="already-admitted"):
        list(
            replay_artifact(
                _parts(raw, 64),
                _pin(raw),
                release_id="release",
                source_digest="1" * 64,
                already_admitted=ShortReader(raw[:-1]),
            )
        )


def test_native_record_frame_rejects_fabricated_scalar_lengths(semantic_db_engine):
    sql = Path(__file__).parents[2] / "src/corpus_structure/semantic/sql/pdf_record_identity.sql"
    with semantic_db_engine.begin() as conn:
        conn.exec_driver_sql(sql.read_text(), execution_options={"no_parameters": True})
        for tag, length in [(b"a", 1), (b"n", 1), (b"b", 0), (b"f", 1)]:
            bad = tag + length.to_bytes(8, "big") + bytes(32)
            with pytest.raises(DBAPIError), conn.begin_nested():
                conn.execute(
                    text(
                        "SELECT ops.pdf_identity_record_frame('s','f','k',ARRAY['x'],ARRAY[:bad])"
                    ),
                    {"bad": bad},
                )
