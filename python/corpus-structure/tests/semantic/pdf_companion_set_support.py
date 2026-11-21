"""Controlled prepared fixtures and independent hostile rows for native refusal controls."""

import pyarrow as pa

from corpus_structure.semantic import _pdf_native_calls as calls
from corpus_structure.semantic.arrow_transfer import copy_arrow_stream
from corpus_structure.semantic.pdf_record_model import record_arrow_schema, record_write_profile


def prepare_controlled_companions(connection, build, family, records, *, start_ordinal=0):
    """Materialize bounded test input using the production pre-adoption encoder."""
    from corpus_structure.semantic.pdf_companion_encoding import prepare_pdf_companion_batches
    from corpus_structure.semantic.pdf_contracts import pdf_context_for_task
    from corpus_structure.semantic.pdf_payloads import prepare_payload_family

    batches = []
    prepare_pdf_companion_batches(
        build,
        family,
        records,
        on_batch=lambda name, batch: batches.append((name, batch)),
        payload_family=(
            prepare_payload_family(pdf_context_for_task(connection, build.task_id))
            if family == "native_metadata"
            else None
        ),
        start_ordinal=start_ordinal,
    )
    return batches


def adopt_controlled_companions(connection, build, family, records, replay_key, *, start_ordinal=0):
    from corpus_structure.semantic.pdf_publication import adopt_prepared_pdf_companion_batches

    batches = prepare_controlled_companions(
        connection, build, family, records, start_ordinal=start_ordinal
    )
    adopt_prepared_pdf_companion_batches(connection, build, batches, replay_key)


def adopt_raw_companion_set(connection, build, rows, *, replay_key, field_rows=()):
    calls.prepare_pdf_companions(connection)
    target = "ops.pdf_stage_companion"
    batch = pa.RecordBatch.from_pylist(rows, schema=record_arrow_schema(target))
    copy_arrow_stream(
        connection,
        record_write_profile(target, release_id=build.release_id),
        target=("pg_temp", "pc_pdf_stage_companion"),
        batches=(batch,),
    )
    if field_rows:
        target = "ops.pdf_stage_companion_field"
        batch = pa.RecordBatch.from_pylist(field_rows, schema=record_arrow_schema(target))
        copy_arrow_stream(
            connection,
            record_write_profile(target, release_id=build.release_id),
            target=("pg_temp", "pc_pdf_stage_companion_field"),
            batches=(batch,),
        )
    calls.adopt_pdf_companions(
        connection,
        build_id=build.build_id,
        task_id=build.task_id,
        attempt=build.attempt,
        holder=build.holder,
        replay_key=replay_key,
    )
