"""Current physical adoption and certification of authorized original PDF bytes.

Native contributor admission proves archived material correspondence before this
owner runs. Original files and their certificate remain immutable provenance.
Only physical carrier columns and current certification custody are rebuilt.
"""

from __future__ import annotations

import json
import os
from dataclasses import replace
from pathlib import Path

import pyarrow as pa

from corpus_structure.ingest.pdf_streaming import _atomic_bytes, _ref

from .pdf_certification import PdfProducerCertification, PdfProducerPayloads


def rebind_pdf_recovery_reply(
    reply, root: Path, *, original_build, original_release, build, on_replay, check_active
):
    """Project declared transport columns; preserve original typed output values."""
    from .pdf_companion_encoding import COMPANION_STAGE_TARGETS
    from .pdf_record_model import record_arrow_schema
    from .pdf_staging import stage_schema

    root.mkdir(parents=True, exist_ok=False)
    sequence = 0

    def rebind(replay):
        nonlocal sequence
        check_active()
        replay.verify()
        if replay.family.startswith("prepared_companion:"):
            target = replay.family.removeprefix("prepared_companion:")
            schema = record_arrow_schema(COMPANION_STAGE_TARGETS[target])
        else:
            schema = stage_schema(replay.family)
        path = root / f"{sequence:08}.arrow"
        sequence += 1
        with pa.memory_map(str(replay.path), "r") as source:
            reader = pa.ipc.open_file(source)
            if not reader.schema.equals(schema, check_metadata=True):
                raise ValueError("original PDF replay differs from current typed transport schema")
            with pa.OSFile(str(path), "wb") as sink, pa.ipc.new_file(sink, schema) as writer:
                for index in range(reader.num_record_batches):
                    check_active()
                    batch = reader.get_batch(index)
                    for name, original, current in (
                        ("product_id", original_build, build.build_id),
                        ("revision_id", original_build, build.build_id),
                        ("release_id", original_release, build.release_id),
                    ):
                        position = schema.get_field_index(name)
                        if position < 0:
                            continue
                        column = batch.column(position)
                        if column.null_count or (
                            len(column)
                            and not column.equals(
                                pa.array([original] * len(column), type=column.type)
                            )
                        ):
                            raise ValueError("original PDF replay has a foreign physical carrier")
                        batch = batch.set_column(
                            position,
                            schema.field(position),
                            pa.array([current] * len(column), type=column.type),
                        )
                    writer.write_batch(batch)
        with path.open("rb") as source:
            os.fsync(source.fileno())
        projected = _ref(path, replay.family, replay.rows)
        on_replay(projected)
        return projected

    return replace(
        reply,
        record_replays=tuple(rebind(replay) for replay in reply.record_replays),
        companion_sets=tuple(
            replace(prepared, replays=tuple(rebind(replay) for replay in prepared.replays))
            for prepared in reply.companion_sets
        ),
    )


def recertify_pdf_recovery(
    reply,
    root: Path,
    *,
    original_release,
    validation_contract,
    lowering_identity,
    build,
    source_digest,
    recipe_digest,
    schema_digest,
    on_replay,
    check_active,
):
    """Rebase a certified exact output after native material equivalence.

    Output validation is reusable because its schema, codecs, producer code and
    validating libraries are unchanged. Actual current records/stream bytes are
    folded again to authenticate the exact original logical output before adoption.
    """
    if reply.certification is None or reply.access_replay is None:
        raise ValueError("recovered PDF lacks original certified output custody")
    reply.certification.verify()
    reply.access_replay.verify()
    original = PdfProducerCertification(**json.loads(reply.certification.path.read_bytes()))
    if (original.kind, original.source_digest, original.recipe_digest, original.schema_digest) != (
        "native",
        source_digest,
        recipe_digest,
        schema_digest,
    ):
        raise ValueError("original PDF certification differs from its material premises")
    root.mkdir(parents=True, exist_ok=False)
    payloads = PdfProducerPayloads(root / "payloads.sqlite", json.loads(validation_contract))
    try:
        payloads.add_replays(reply.record_replays, check_active=check_active)
        payloads.add_companion_replays(reply.companion_sets, check_active=check_active)
        check_active()
        original_digest = payloads.logical_digest(
            release_id=original_release,
            source_digest=source_digest,
            recipe_digest=recipe_digest,
            schema_digest=schema_digest,
            kind="native",
            target_meanings={},
        )
        if (
            original_digest != original.logical_digest
            or payloads.stream_inventory_digest != original.stream_inventory_digest
        ):
            raise ValueError("recovered PDF actual output differs from original certification")
        certificate = replace(
            original, logical_digest=original_digest, lowering_identity=lowering_identity
        )
    finally:
        payloads.close()
    replay = _atomic_bytes(
        root / "certification.json", certificate.to_bytes(), "producer_certification"
    )
    on_replay(replay)
    return replace(reply, certification=replay)
