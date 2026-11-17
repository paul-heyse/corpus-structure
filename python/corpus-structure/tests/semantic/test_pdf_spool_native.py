"""Original producer admission and exact contributor membership use the live native fence."""

import json
from hashlib import sha256

from sqlalchemy import text

from corpus_structure.ingest.pdf_build_spool import (
    PdfBuildSpool, PdfSpoolPremises, PdfSpoolProducerBasis, selected_replay_bytes,
)
from corpus_structure.ingest.pdf_stream_types import PdfReplayRef
from native_refusals import native_refusal
from semantic.pdf_staging_support import private_build as private_build


def test_native_spool_contributor_preserves_original_fence_and_rejects_invented_membership(
    private_build, commit_writer_engine, tmp_path,
):
    build = private_build
    with commit_writer_engine.begin() as connection:
        runtime = connection.scalar(text("SELECT request.runtime_id FROM ops.task task JOIN ops.data_request request ON request.id=task.data_request_id WHERE task.id=:task"), {"task": build.task_id})
        basis = connection.execute(text("SELECT * FROM ops.read_pdf_producer_basis(:task,:attempt,:holder,:runtime)"),
            dict(task=build.task_id, attempt=build.attempt, holder=build.holder, runtime=runtime)).mappings().one()
        premises = PdfSpoolPremises(PdfSpoolProducerBasis(**dict(basis)), build.source_digest,
            build.recipe_digest, build.schema_digest, "a" * 64, None, (("docling", "2.148.0"),))
        with PdfBuildSpool(tmp_path, build_id=build.build_id, task_id=build.task_id,
                           attempt=build.attempt, holder=build.holder, check_active=lambda: None) as spool:
            args = dict(build=build.build_id, task=build.task_id, attempt=build.attempt,
                        holder=build.holder, runtime=runtime, premises=premises.to_bytes(),
                        **spool.writer_lease.identity)
            producer = connection.scalar(text("SELECT ops.register_pdf_spool_producer(:build,:task,:attempt,:holder,:runtime,:device,:inode,:premises)"), args)
            spool.declare_premises(premises, producer)
            path = spool.root / "native.arrow"
            path.write_bytes(b"retained original bytes")
            replay = PdfReplayRef(path, sha256(path.read_bytes()).hexdigest(), path.stat().st_size, "native")
            spool.append(replay)
            arguments = dict(build=build.build_id, task=build.task_id, attempt=build.attempt,
                             holder=build.holder, runtime=runtime, producer=producer,
                             manifest=spool.path.read_bytes(), selected=selected_replay_bytes(spool.root, (replay,)))
            statement = text("SELECT ops.register_pdf_spool_contributor(:build,:task,:attempt,:holder,:runtime,:producer,:manifest,:selected)")
            contributor = connection.scalar(statement, arguments)
            assert connection.scalar(statement, arguments) == contributor
            receipt = connection.execute(text("SELECT * FROM ops.read_pdf_spool_contributors(:build,:task,:attempt,:holder)"), arguments).mappings().all()
            assert len(receipt) == 1
            assert receipt[0]["producer_id"] == producer
            assert receipt[0]["producer_attempt"] == build.attempt
            assert receipt[0]["producer_holder"] == build.holder
            assert receipt[0]["runtime_id"] == runtime
            assert receipt[0]["runtime_manifest_digest"] == basis["runtime_manifest_digest"]
            assert receipt[0]["manifest_digest"] == sha256(spool.path.read_bytes()).hexdigest()
            selected = json.loads(arguments["selected"])
            selected[0]["digest"] = "f" * 64
            with native_refusal("23514", message="selected PDF replay differs from original manifest membership"), connection.begin_nested():
                connection.scalar(statement, {**arguments, "selected": json.dumps(selected).encode()})
            forged = [json.loads(line) for line in arguments["manifest"].splitlines()]
            forged[0]["writer"]["inode"] += 1
            with native_refusal("23514", message="PDF manifest differs from immutable original producer custody"), connection.begin_nested():
                connection.scalar(statement, {**arguments, "manifest": b"".join(json.dumps(value).encode()+b"\n" for value in forged)})
