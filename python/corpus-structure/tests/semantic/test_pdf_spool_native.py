"""Original producer admission and exact contributor membership use the live native fence."""

import json
from hashlib import sha256

import pytest
from docling_core.types.doc import DocItemLabel, DoclingDocument, Size
from native_refusals import native_refusal
from pdf_acceptance_support import prepare_pdf_document
from sqlalchemy import text

from corpus_structure.core.db.lifetime import BorrowerCancellation
from corpus_structure.ingest.pdf_build_spool import (
    PdfBuildSpool,
    PdfSpoolPremises,
    PdfSpoolProducerBasis,
    selected_replay_bytes,
)
from corpus_structure.ingest.pdf_stream_types import PdfReplayRef
from corpus_structure.orchestrate.pdf_streaming import _adopt_pdf_document
from corpus_structure.semantic.pdf_staging import inspect_pdf_progress
from semantic.pdf_staging_support import create_private_build as create_private_build


def test_native_spool_contributor_preserves_original_fence_and_rejects_invented_membership(
    create_private_build,
    commit_writer_engine,
    tmp_path,
):
    build = create_private_build()
    runtime = create_private_build.kernel.runtime
    with commit_writer_engine.begin() as connection:
        basis = (
            connection.execute(
                text("SELECT * FROM ops.read_pdf_producer_basis(:task,:attempt,:holder,:runtime)"),
                dict(
                    task=build.task_id, attempt=build.attempt, holder=build.holder, runtime=runtime
                ),
            )
            .mappings()
            .one()
        )
        premises = PdfSpoolPremises(
            PdfSpoolProducerBasis(**dict(basis)),
            build.source_digest,
            build.recipe_digest,
            build.schema_digest,
            "a" * 64,
            None,
            (("docling", "2.148.0"),),
        )
        with PdfBuildSpool(
            tmp_path,
            build_id=build.build_id,
            task_id=build.task_id,
            attempt=build.attempt,
            holder=build.holder,
            check_active=lambda: None,
        ) as spool:
            args = dict(
                build=build.build_id,
                task=build.task_id,
                attempt=build.attempt,
                holder=build.holder,
                runtime=runtime,
                premises=premises.to_bytes(),
                **spool.writer_lease.identity,
            )
            producer = connection.scalar(
                text(
                    "SELECT ops.register_pdf_spool_producer(:build,:task,:attempt,:holder,:runtime,:device,:inode,:premises)"
                ),
                args,
            )
            spool.declare_premises(premises, producer)
            path = spool.root / "native.arrow"
            path.write_bytes(b"retained original bytes")
            replay = PdfReplayRef(
                path, sha256(path.read_bytes()).hexdigest(), path.stat().st_size, "native"
            )
            spool.append(replay)
            arguments = dict(
                build=build.build_id,
                task=build.task_id,
                attempt=build.attempt,
                holder=build.holder,
                runtime=runtime,
                producer=producer,
                manifest=spool.path.read_bytes(),
                selected=selected_replay_bytes(spool.root, (replay,)),
            )
            statement = text(
                "SELECT ops.register_pdf_spool_contributor(:build,:task,:attempt,:holder,:runtime,:producer,:manifest,:selected)"
            )
            contributor = connection.scalar(statement, arguments)
            assert connection.scalar(statement, arguments) == contributor
            receipt = (
                connection.execute(
                    text(
                        "SELECT * FROM ops.read_pdf_spool_contributors(:build,:task,:attempt,:holder)"
                    ),
                    arguments,
                )
                .mappings()
                .all()
            )
            assert len(receipt) == 1
            assert receipt[0]["producer_id"] == producer
            assert receipt[0]["producer_attempt"] == build.attempt
            assert receipt[0]["producer_holder"] == build.holder
            assert receipt[0]["runtime_id"] == runtime
            assert receipt[0]["runtime_manifest_digest"] == basis["runtime_manifest_digest"]
            assert receipt[0]["manifest_digest"] == sha256(spool.path.read_bytes()).hexdigest()
            selected = json.loads(arguments["selected"])
            selected[0]["digest"] = "f" * 64
            with (
                native_refusal(
                    "23514", message="selected PDF replay differs from original manifest membership"
                ),
                connection.begin_nested(),
            ):
                connection.scalar(
                    statement, {**arguments, "selected": json.dumps(selected).encode()}
                )
            forged = [json.loads(line) for line in arguments["manifest"].splitlines()]
            forged[0]["writer"]["inode"] += 1
            with (
                native_refusal(
                    "23514", message="PDF manifest differs from immutable original producer custody"
                ),
                connection.begin_nested(),
            ):
                connection.scalar(
                    statement,
                    {
                        **arguments,
                        "manifest": b"".join(
                            json.dumps(value).encode() + b"\n" for value in forged
                        ),
                    },
                )


def test_native_complete_document_replays_atomically_under_a_new_build(
    create_private_build, commit_writer_engine, tmp_path
):
    original = create_private_build()
    adopter = create_private_build(case="unknown-cell-coverage")
    assert adopter.build_id != original.build_id
    document = DoclingDocument(name="Exact retained publication")
    document.add_page(page_no=1, size=Size(width=200, height=300))
    document.add_text(label=DocItemLabel.TEXT, text="Same independent text.")
    prepared = prepare_pdf_document(commit_writer_engine, original, tmp_path, document)
    records, companions, access, _ = prepared
    files = (*records, *(replay for group in companions for replay in group.replays), access)
    original_bytes = {replay.path: replay.read_bytes() for replay in files}

    def adopt(build):
        _adopt_pdf_document(
            commit_writer_engine,
            build,
            *prepared,
            cancellation=BorrowerCancellation(),
            check_active=lambda: None,
        )

    adopt(original)
    late = companions[-1].replays[-1].path
    late.write_bytes(bytes(len(original_bytes[late])))
    with pytest.raises(ValueError, match="replay bytes changed"):
        adopt(adopter)
    with commit_writer_engine.begin() as connection:
        assert not inspect_pdf_progress(connection, adopter)
    late.write_bytes(original_bytes[late])

    adopt(adopter)
    with commit_writer_engine.begin() as connection:
        first = inspect_pdf_progress(connection, original)
        second = inspect_pdf_progress(connection, adopter)
    (original_header,) = [row for row in first if row.replay_key.startswith("ipc:header:")]
    (adopted_header,) = [row for row in second if row.replay_key.startswith("ipc:header:")]
    assert (original_header.replay_key, original_header.row_count) == (
        adopted_header.replay_key,
        adopted_header.row_count,
    )
    assert all(entry.build_id == adopter.build_id for entry in second)
    assert {replay.path: replay.read_bytes() for replay in files} == original_bytes
