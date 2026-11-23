"""Actual shared byte ownership, pending fences and project isolation."""

from hashlib import sha256

import pyarrow as pa
import pytest
from native_refusals import native_refusal
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError

from corpus_structure.semantic.native_objects import native_owner
from corpus_structure.semantic.pdf_record_identity import (
    ArtifactPart,
    ArtifactPin,
    byte_root,
    emit_parts,
    replay_artifact,
)
from corpus_structure.semantic.pdf_record_model import (
    artifact_part_upload_table,
    record_arrow_schema,
)
from corpus_structure.semantic.pdf_shared_streams import (
    PdfSharedStreamTransfer,
    verified_shared_stream_ids,
)
from corpus_structure.semantic.pdf_staging import (
    STAGE_FAMILIES,
    UPLOAD_STAGE_FAMILIES,
    abandon_pdf_build,
    adopt_pdf_batch,
    stage_schema,
)
from semantic.pdf_staging_support import create_private_build as create_private_build

PROFILE = "pdf-record-scalar-v1:s"
BODY = b"a" * 65536 + b"independent final shared bytes"


def descriptor(build, *, body=BODY, stream="shared-scalar"):
    length, root = byte_root((body,))
    return dict(
        product_id=build.build_id,
        revision_id=build.build_id,
        stream_id=stream,
        byte_length=length,
        serialization_sha256=sha256(body).hexdigest(),
        byte_root=root.hex(),
        encoding_profile=PROFILE,
    )


def part_rows(build, *, body=BODY, stream="shared-scalar"):
    return [
        dict(
            product_id=build.build_id,
            revision_id=build.build_id,
            stream_id=stream,
            ordinal=part.ordinal,
            byte_offset=part.offset,
            byte_length=part.byte_length,
            body=part.body,
            sha256_digest=part.sha256_digest,
        )
        for part in emit_parts(stream, (body,))
    ]


def packet(family, rows):
    return {family: (pa.RecordBatch.from_pylist(rows, schema=stage_schema(family)),)}


def count_content(connection):
    return tuple(
        connection.execute(
            text(
                "SELECT (SELECT count(*) FROM ops.pdf_shared_stream),"
                "(SELECT count(*) FROM ops.pdf_shared_stream_part),"
                "(SELECT count(*) FROM ops.pdf_shared_stream_verification)"
            )
        ).one()
    )


def _expire_task(connection, task_id):
    # The test advances a controlled clock boundary under the fixture's
    # publisher authority; the worker must still observe the expired fence.
    with native_owner(connection, "corpus_sem_publisher"):
        changed = connection.execute(
            text(
                "UPDATE ops.task SET lease_until=clock_timestamp()-interval '1 second' WHERE id=:task"
            ),
            {"task": task_id},
        )
        assert changed.rowcount == 1


def test_part_wire_remains_model_owned_without_a_per_build_part_store():
    from corpus_structure.semantic.metadata import get_metadata

    assert "ops.pdf_artifact_part" not in get_metadata().tables
    assert "ops.pdf_stage_artifact_part" not in get_metadata().tables
    assert "artifact_part" not in STAGE_FAMILIES and "artifact_part" in UPLOAD_STAGE_FAMILIES
    upload = artifact_part_upload_table()
    assert record_arrow_schema("ops.pdf_stage_artifact_part").names == list(upload.c.keys())
    assert "body" in upload.c and upload.c.body.nullable is False


def test_equal_stage_streams_store_parts_once_and_descriptor_only_reuse_is_real(
    create_private_build,
    commit_writer_engine,
    commit_db_engine,
):
    first = create_private_build()
    second = create_private_build(case="unknown-cell-coverage")
    with commit_writer_engine.begin() as connection:
        adopt_pdf_batch(
            connection, first, "descriptor", packet("artifact_stream", [descriptor(first)])
        )
        adopt_pdf_batch(connection, first, "parts", packet("artifact_part", part_rows(first)))
    with commit_writer_engine.begin() as connection:
        assert verified_shared_stream_ids(connection, second, [descriptor(second)]) == {
            "shared-scalar"
        }
        # This second independent stage sends no part packet at all.
        adopt_pdf_batch(
            connection, second, "descriptor", packet("artifact_stream", [descriptor(second)])
        )
    with commit_db_engine.begin() as connection:
        assert count_content(connection) == (1, 2, 1)
        for build in (first, second):
            rows = (
                connection.execute(
                    text(
                        "SELECT * FROM ops.pdf_artifact_parts(:build,:build,true) ORDER BY ordinal"
                    ),
                    dict(build=build.build_id),
                )
                .mappings()
                .all()
            )
            assert [row["ordinal"] for row in rows] == [0, 1]
            assert b"".join(row["body"] for row in rows) == BODY
        assert (
            connection.scalar(
                text(
                    "SELECT count(*) FROM ops.pdf_stage_artifact_stream WHERE stream_id='shared-scalar'"
                )
            )
            == 2
        )
    with commit_writer_engine.begin() as connection:
        changed = part_rows(second)
        changed[0]["body"] = b"x" * 65536
        changed[0]["sha256_digest"] = sha256(changed[0]["body"]).hexdigest()
        with (
            native_refusal("23514", message="shared stream part replay differs"),
            connection.begin_nested(),
        ):
            adopt_pdf_batch(connection, second, "changed", packet("artifact_part", changed))


def test_live_pending_owner_refuses_and_expired_owner_reclaim_preserves_fences(
    create_private_build,
    commit_writer_engine,
    commit_db_engine,
):
    first = create_private_build()
    second = create_private_build(case="unknown-cell-coverage")
    with commit_writer_engine.begin() as connection:
        adopt_pdf_batch(
            connection, first, "descriptor", packet("artifact_stream", [descriptor(first)])
        )
        adopt_pdf_batch(connection, first, "partial", packet("artifact_part", part_rows(first)[:1]))
    with commit_writer_engine.begin() as connection:
        assert verified_shared_stream_ids(connection, second, [descriptor(second)]) == set()
        with pytest.raises(DBAPIError) as refused, connection.begin_nested():
            adopt_pdf_batch(
                connection, second, "descriptor", packet("artifact_stream", [descriptor(second)])
            )
        assert getattr(refused.value.orig, "sqlstate", None) == "55P03"
    with commit_db_engine.begin() as connection:
        assert count_content(connection) == (1, 1, 0)
        _expire_task(connection, first.task_id)
    with commit_writer_engine.begin() as connection:
        with pytest.raises(DBAPIError) as refused, connection.begin_nested():
            adopt_pdf_batch(
                connection, first, "late", packet("artifact_part", part_rows(first)[1:])
            )
        assert getattr(refused.value.orig, "sqlstate", None) == "P0004"
        # Reclaim authenticates the old closed append fence, drops only pending
        # content, then admits this actual new owner. No byte is trusted by key alone.
        adopt_pdf_batch(
            connection, second, "descriptor", packet("artifact_stream", [descriptor(second)])
        )
        adopt_pdf_batch(connection, second, "parts", packet("artifact_part", part_rows(second)))
    with commit_db_engine.begin() as connection:
        assert count_content(connection) == (1, 2, 1)
        assert (
            connection.scalar(text("SELECT owner_build_id FROM ops.pdf_shared_stream"))
            == second.build_id
        )


def test_abandon_cleans_only_pending_content_and_verified_bytes_refuse_mutation(
    create_private_build,
    commit_writer_engine,
    commit_db_engine,
):
    first = create_private_build()
    second = create_private_build(case="unknown-cell-coverage")
    with commit_writer_engine.begin() as connection:
        adopt_pdf_batch(
            connection, first, "descriptor", packet("artifact_stream", [descriptor(first)])
        )
        adopt_pdf_batch(connection, first, "partial", packet("artifact_part", part_rows(first)[:1]))
        abandon_pdf_build(connection, first)
    with commit_db_engine.begin() as connection:
        assert count_content(connection) == (0, 0, 0)
    with commit_writer_engine.begin() as connection:
        adopt_pdf_batch(
            connection, second, "descriptor", packet("artifact_stream", [descriptor(second)])
        )
        adopt_pdf_batch(connection, second, "parts", packet("artifact_part", part_rows(second)))
        abandon_pdf_build(connection, second)
    with commit_db_engine.begin() as connection:
        assert count_content(connection) == (1, 2, 1)
        for statement, reason in (
            ("DELETE FROM ops.pdf_shared_stream_part", "verified content is immutable"),
            (
                "UPDATE ops.pdf_shared_stream_part SET body=body",
                "shared content cannot be updated or truncated",
            ),
            (
                "TRUNCATE ops.pdf_shared_stream_part",
                "shared content cannot be updated or truncated",
            ),
            ("DELETE FROM ops.pdf_shared_stream", "verified content is immutable"),
        ):
            with native_refusal("23514", message=reason), connection.begin_nested():
                connection.execute(text(statement))
            assert count_content(connection) == (1, 2, 1)


def test_shared_part_tampering_refuses_every_referencing_build(
    create_private_build,
    commit_writer_engine,
    commit_db_engine,
):
    first = create_private_build()
    second = create_private_build(case="unknown-cell-coverage")
    with commit_writer_engine.begin() as connection:
        adopt_pdf_batch(
            connection, first, "descriptor", packet("artifact_stream", [descriptor(first)])
        )
        adopt_pdf_batch(connection, first, "parts", packet("artifact_part", part_rows(first)))
        adopt_pdf_batch(
            connection, second, "descriptor", packet("artifact_stream", [descriptor(second)])
        )
    with commit_db_engine.begin() as connection:
        # Controlled corruption bypasses the normal immutable guard and the local
        # part checksum, so each consumer must still detect the wrong stream root.
        connection.execute(
            text(
                "ALTER TABLE ops.pdf_shared_stream_part DISABLE TRIGGER pdf_shared_content_mutation"
            )
        )
        connection.execute(
            text(
                "UPDATE ops.pdf_shared_stream_part SET body=repeat('x',65536)::bytea,sha256_digest=encode(sha256(repeat('x',65536)::bytea),'hex') WHERE ordinal=0"
            )
        )
        connection.execute(
            text(
                "ALTER TABLE ops.pdf_shared_stream_part ENABLE TRIGGER pdf_shared_content_mutation"
            )
        )
        for build in (first, second):
            rows = (
                connection.execute(
                    text(
                        "SELECT * FROM ops.pdf_artifact_parts(:build,:build,true) ORDER BY ordinal"
                    ),
                    dict(build=build.build_id),
                )
                .mappings()
                .all()
            )
            selected = descriptor(build)
            pin = ArtifactPin(
                "shared-scalar",
                build.release_id,
                build.source_digest,
                len(BODY),
                selected["serialization_sha256"],
                bytes.fromhex(selected["byte_root"]),
            )
            parts = [
                ArtifactPart(
                    "shared-scalar",
                    row["ordinal"],
                    row["byte_offset"],
                    row["byte_length"],
                    row["body"],
                    row["sha256_digest"],
                )
                for row in rows
            ]
            with pytest.raises(ValueError):
                tuple(
                    replay_artifact(
                        parts, pin, release_id=build.release_id, source_digest=build.source_digest
                    )
                )


def test_transport_omission_rechecks_the_actual_build_and_keeps_source_packets(monkeypatch):
    from types import SimpleNamespace

    from corpus_structure.semantic import pdf_shared_streams

    build = SimpleNamespace(build_id="build")
    transfer = PdfSharedStreamTransfer()
    probes = []

    def probe(connection, owned, rows):
        probes.append((owned, tuple(rows)))
        return frozenset({"shared-scalar"})

    monkeypatch.setattr(pdf_shared_streams, "verified_shared_stream_ids", probe)
    assert not transfer.omit_verified_parts(
        None, build, packet("artifact_stream", [descriptor(build)])
    )
    source = packet("artifact_part", part_rows(build))
    assert transfer.omit_verified_parts(None, build, source)
    assert transfer.omit_verified_parts(None, build, source)
    assert len(probes) == 2 and all(owned is build for owned, _ in probes)
    assert source["artifact_part"][0].num_rows == 2


@pytest.mark.parametrize("field", ["product_id", "revision_id"])
@pytest.mark.parametrize("value", [None, "another-build"])
def test_transport_omission_refuses_changed_or_null_build_before_probe(monkeypatch, field, value):
    from types import SimpleNamespace

    from corpus_structure.semantic import pdf_shared_streams

    build = SimpleNamespace(build_id="build")
    transfer = PdfSharedStreamTransfer()
    probes = []
    monkeypatch.setattr(
        pdf_shared_streams, "verified_shared_stream_ids", lambda *args: probes.append(args)
    )
    transfer.omit_verified_parts(None, build, packet("artifact_stream", [descriptor(build)]))
    rows = part_rows(build)
    rows[-1][field] = value
    with pytest.raises(ValueError, match="changes its owned build"):
        transfer.omit_verified_parts(None, build, packet("artifact_part", rows))
    assert probes == []


def test_transport_omission_probes_distinct_streams_across_batches(monkeypatch):
    from types import SimpleNamespace

    from corpus_structure.semantic import pdf_shared_streams

    build = SimpleNamespace(build_id="build")
    transfer = PdfSharedStreamTransfer()
    probes = []

    def probe(connection, owned, rows):
        probes.append(tuple(row["stream_id"] for row in rows))
        return frozenset({"first"})

    monkeypatch.setattr(pdf_shared_streams, "verified_shared_stream_ids", probe)
    transfer.omit_verified_parts(
        None,
        build,
        packet("artifact_stream", [descriptor(build, stream=name) for name in ("first", "second")]),
    )
    first = packet("artifact_part", part_rows(build, stream="first"))["artifact_part"]
    second = packet("artifact_part", part_rows(build, stream="second"))["artifact_part"]
    assert not transfer.omit_verified_parts(
        None, build, {"artifact_part": (*first, *first, *second)}
    )
    assert probes == [("first", "second")]


def test_another_project_cannot_reuse_the_verified_key(
    create_private_build,
    commit_writer_engine,
    commit_db_engine,
    tmp_path,
    monkeypatch,
):
    from corpus_structure.core.evidence import document_key
    from corpus_structure.semantic.data_operation_storage import DataOperationStorage
    from corpus_structure.semantic.identifiers import ProjectId, ReleaseId
    from corpus_structure.semantic.original_documents import register_original_document
    from semantic import pdf_staging_support

    first = create_private_build()
    with commit_writer_engine.begin() as connection:
        adopt_pdf_batch(
            connection, first, "descriptor", packet("artifact_stream", [descriptor(first)])
        )
        adopt_pdf_batch(connection, first, "parts", packet("artifact_part", part_rows(first)))
    other_project = "pdf-shared-other-project"
    original = create_private_build.original
    original_path = tmp_path / "other-original.pdf"
    original_path.write_bytes(original)
    with commit_writer_engine.begin() as connection:
        DataOperationStorage(connection).initialize_source_project(
            {
                "project_id": ProjectId(other_project),
                "release_id": ReleaseId(first.release_id),
            }
        )
        register_original_document(
            connection,
            prepared=create_private_build.kernel.prepared,
            project_id=other_project,
            source_uri="file:pdf-stage",
            original_path=str(original_path),
            original=original,
            mime="application/pdf",
        )
    # This is a real second project/original/request/claim, not a relabelled build ID.
    with monkeypatch.context() as scope:
        scope.setattr(pdf_staging_support, "_PROJECT", other_project)
        factory = pdf_staging_support._PrivatePdfBuildFactory(
            create_private_build.kernel,
            create_private_build.writer,
            create_private_build.admitter,
            original,
            create_private_build.recipe,
            document_key(other_project, "file:pdf-stage", sha256(original).hexdigest()),
        )
        second = factory()
    with commit_writer_engine.begin() as connection:
        assert verified_shared_stream_ids(connection, second, [descriptor(second)]) == set()
        adopt_pdf_batch(
            connection, second, "descriptor", packet("artifact_stream", [descriptor(second)])
        )
    with commit_db_engine.begin() as connection:
        assert tuple(
            connection.execute(
                text(
                    "SELECT project_id FROM ops.pdf_shared_stream_verification ORDER BY project_id"
                )
            ).scalars()
        ) == (create_private_build.project_id,)
        # A descriptor never borrows another project's stored part population.
        assert (
            connection.scalar(
                text("SELECT count(*) FROM ops.pdf_artifact_parts(:build,:build,true)"),
                dict(build=second.build_id),
            )
            == 0
        )
    with commit_writer_engine.begin() as connection:
        adopt_pdf_batch(connection, second, "parts", packet("artifact_part", part_rows(second)))
    with commit_db_engine.begin() as connection:
        assert count_content(connection) == (2, 4, 2)


def test_pending_reclaim_does_not_race_a_locked_original_append_fence(
    create_private_build,
    commit_writer_engine,
    commit_db_engine,
):
    first = create_private_build()
    second = create_private_build(case="unknown-cell-coverage")
    with commit_writer_engine.begin() as connection:
        adopt_pdf_batch(
            connection, first, "descriptor", packet("artifact_stream", [descriptor(first)])
        )
        adopt_pdf_batch(connection, first, "partial", packet("artifact_part", part_rows(first)[:1]))
    with commit_db_engine.begin() as connection:
        _expire_task(connection, first.task_id)
    # A genuinely concurrent connection holds the old task fence. Reclaim must
    # refuse NOWAIT; it cannot infer retirement merely from an earlier timestamp.
    with commit_db_engine.connect() as blocker, blocker.begin():
        blocker.execute(
            text("SELECT id FROM ops.task WHERE id=:task FOR UPDATE"), dict(task=first.task_id)
        )
        with commit_writer_engine.begin() as connection:
            with pytest.raises(DBAPIError) as refused, connection.begin_nested():
                adopt_pdf_batch(
                    connection,
                    second,
                    "descriptor",
                    packet("artifact_stream", [descriptor(second)]),
                )
            assert getattr(refused.value.orig, "sqlstate", None) == "55P03"
    with commit_writer_engine.begin() as connection:
        adopt_pdf_batch(
            connection, second, "descriptor", packet("artifact_stream", [descriptor(second)])
        )
        adopt_pdf_batch(connection, second, "parts", packet("artifact_part", part_rows(second)))
    with commit_db_engine.begin() as connection:
        assert count_content(connection) == (1, 2, 1)


def test_replay_and_companion_producers_emit_descriptors_before_complete_parts(tmp_path):
    from corpus_structure.ingest.pdf_stream_types import PdfReplayRef
    from corpus_structure.ingest.pdf_streaming import iter_replay_artifact_batches
    from corpus_structure.semantic.pdf_companion_encoding import (
        PdfCompanionEncodingBasis,
        prepare_pdf_companion_batches,
    )

    source = tmp_path / "payload"
    source.write_bytes(BODY)
    batches = tuple(
        iter_replay_artifact_batches(
            PdfReplayRef.from_path(source, "candidate"),
            build_id="build",
            stream_id="candidate",
            encoding_profile=PROFILE,
        )
    )
    assert batches[0][0] == "artifact_stream"
    assert (
        b"".join(
            row["body"]
            for family, batch in batches
            if family == "artifact_part"
            for row in batch.to_pylist()
        )
        == BODY
    )
    prepared = []
    prepare_pdf_companion_batches(
        PdfCompanionEncodingBasis("build", "release"),
        "occurrence",
        ({"occurrence_id": "o", "kind": "caption", "text": "x" * 100000},),
        on_batch=lambda name, batch: prepared.append((name, batch)),
        payload_family=None,
    )
    declared = set()
    for family, batch in prepared:
        if family == "stream":
            declared.update(batch.column("stream_id").to_pylist())
        elif family == "part":
            assert set(batch.column("stream_id").to_pylist()) <= declared
    assert (
        b"".join(
            row["body"]
            for family, batch in prepared
            if family == "part"
            for row in batch.to_pylist()
        )
        == b"x" * 100000
    )


def test_same_build_new_attempt_replays_exact_receipts_after_pending_reclaim(
    create_private_build,
    commit_writer_engine,
    commit_db_engine,
):
    from dataclasses import replace

    from corpus_structure.semantic.pdf_staging import resume_pdf_build

    build = create_private_build()
    with commit_writer_engine.begin() as connection:
        stream_receipt = adopt_pdf_batch(
            connection, build, "descriptor", packet("artifact_stream", [descriptor(build)])
        )
        prefix_receipt = adopt_pdf_batch(
            connection, build, "prefix", packet("artifact_part", part_rows(build)[:1])
        )
    with commit_db_engine.begin() as connection:
        _expire_task(connection, build.task_id)
    with commit_writer_engine.begin() as connection:
        claimed = create_private_build.reclaim(connection, build, holder="next-byte-owner")
        resumed = resume_pdf_build(
            connection, build, attempt=claimed["attempt"], holder=claimed["holder"]
        )
        assert resumed == replace(build, attempt=claimed["attempt"], holder=claimed["holder"])
        assert (
            adopt_pdf_batch(
                connection, resumed, "descriptor", packet("artifact_stream", [descriptor(resumed)])
            )
            == stream_receipt
        )
        assert (
            adopt_pdf_batch(
                connection, resumed, "prefix", packet("artifact_part", part_rows(resumed)[:1])
            )
            == prefix_receipt
        )
        adopt_pdf_batch(
            connection, resumed, "suffix", packet("artifact_part", part_rows(resumed)[1:])
        )
    with commit_db_engine.begin() as connection:
        assert count_content(connection) == (1, 2, 1)
        assert (
            connection.scalar(text("SELECT owner_attempt FROM ops.pdf_shared_stream"))
            == build.attempt + 1
        )


def test_supplied_physical_sources_bind_actual_arrow_and_upload_only_schema_ids():
    import json

    import yaml

    from corpus_structure.schema.physical import compile_physical
    from corpus_structure.semantic.metadata import get_metadata

    sources = dict(get_metadata().info["physical_sources"])
    owner = yaml.safe_load(sources["pdf-records.yaml"])
    owner["classes"]["PdfArtifactPart"]["attributes"]["byte_offset"]["minimum_value"] = 7
    sources["pdf-records.yaml"] = yaml.safe_dump(owner, sort_keys=False).encode()
    supplied = compile_physical(sources, linkml_types=get_metadata().info["physical_linkml_types"])
    expected_id = supplied.info["physical_model_id"]
    assert expected_id != get_metadata().info["physical_model_id"]
    ordinary = record_arrow_schema("ops.pdf_stage_native", model=supplied)
    upload = record_arrow_schema("ops.pdf_stage_artifact_part", model=supplied)
    assert ordinary.metadata[b"physical_model_id"].decode() == expected_id
    assert upload.metadata[b"physical_model_id"].decode() == expected_id
    assert json.loads(upload.field("byte_offset").metadata[b"constraints"])["minimum"] == 7
    overlay = artifact_part_upload_table(supplied).metadata
    assert overlay.info["pdf_upload_only"]
    assert overlay.info["physical_model_id"] == expected_id
    assert overlay.info["physical_sources"] == supplied.info["physical_sources"]
    assert "ops.pdf_stage_artifact_part" not in supplied.tables
