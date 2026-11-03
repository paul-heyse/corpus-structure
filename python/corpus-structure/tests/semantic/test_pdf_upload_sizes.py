"""Native binary payload budgets must not count a JSON hex rendering as wire data."""

from hashlib import sha256

import pyarrow as pa
import pytest
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError

from corpus_structure.semantic.pdf_staging import adopt_pdf_batch, stage_schema

from .pdf_staging_support import private_build as private_build


def test_four_megabyte_binary_batch_uses_declared_native_extent(
    private_build, semantic_writer_engine
):
    build = private_build
    block = b"x" * 65536
    rows = [
        dict(
            product_id=build.build_id,
            revision_id=build.build_id,
            stream_id="binary-budget",
            ordinal=i,
            byte_offset=i * len(block),
            byte_length=len(block),
            body=block,
            sha256_digest=sha256(block).hexdigest(),
        )
        for i in range(64)
    ]
    batch = pa.RecordBatch.from_pylist(rows, schema=stage_schema("artifact_part"))
    assert 4 * 1024**2 < batch.nbytes < 8 * 1024**2
    with semantic_writer_engine.begin() as conn:
        receipt = adopt_pdf_batch(conn, build, "native-binary-budget", {"artifact_part": (batch,)})
        assert receipt.row_count == 64
        # The formerly used whole-row JSON size exceeds the unchanged8MiB native limit.
        old_size = conn.execute(
            text("""
          SELECT sum(octet_length(to_jsonb(p)::text))
          FROM pg_temp.ps_pdf_stage_artifact_part p WHERE product_id=:build
        """),
            dict(build=build.build_id),
        ).scalar_one()
        assert old_size > 8 * 1024**2


def test_native_extent_limit_is_enforced_independently_of_arrow_preflight(
    private_build, semantic_writer_engine
):
    build = private_build
    block = b"x" * 65536
    params = dict(
        build=build.build_id,
        task=build.task_id,
        attempt=build.attempt,
        holder=build.holder,
        body=block,
        sha=sha256(block).hexdigest(),
    )
    with (
        pytest.raises(DBAPIError, match="private PDF upload profile exceeded"),
        semantic_writer_engine.begin() as conn,
    ):
        conn.execute(text("SELECT ops.prepare_pdf_stage(:build,:task,:attempt,:holder)"), params)
        conn.execute(
            text("""
          INSERT INTO pg_temp.ps_pdf_stage_artifact_part
            (product_id,revision_id,stream_id,ordinal,byte_offset,byte_length,body,sha256_digest)
          SELECT :build,:build,'overflow',i,i*65536,65536,:body,:sha
          FROM generate_series(0,127) i
        """),
            params,
        )
        conn.execute(
            text("SELECT * FROM ops.adopt_pdf_batch(:build,:task,:attempt,:holder,'overflow')"),
            params,
        )
