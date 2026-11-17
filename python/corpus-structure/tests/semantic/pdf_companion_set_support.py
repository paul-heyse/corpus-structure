"""Independent raw-row construction for protected companion set refusal controls."""

import pyarrow as pa

from corpus_structure.semantic import _pdf_native_calls as calls
from corpus_structure.semantic.arrow_transfer import copy_arrow_stream
from corpus_structure.semantic.pdf_record_model import record_arrow_schema, record_write_profile


def adopt_raw_companion_set(connection, build, rows, *, replay_key, field_rows=()):
    calls.prepare_pdf_companions(connection)
    target = "ops.pdf_stage_companion"
    batch = pa.RecordBatch.from_pylist(rows, schema=record_arrow_schema(target))
    copy_arrow_stream(connection, record_write_profile(target, release_id=build.release_id),
                      target=("pg_temp", "pc_pdf_stage_companion"), batches=(batch,))
    if field_rows:
        target = "ops.pdf_stage_companion_field"
        batch = pa.RecordBatch.from_pylist(field_rows, schema=record_arrow_schema(target))
        copy_arrow_stream(connection, record_write_profile(target, release_id=build.release_id),
                          target=("pg_temp", "pc_pdf_stage_companion_field"), batches=(batch,))
    calls.adopt_pdf_companions(connection, build_id=build.build_id, task_id=build.task_id,
                              attempt=build.attempt, holder=build.holder, replay_key=replay_key)
