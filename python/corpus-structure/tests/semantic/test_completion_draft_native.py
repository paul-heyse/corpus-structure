"""Actual private current-target original execution and adopter correspondence."""

from dataclasses import replace
from hashlib import sha256
from typing import Any, cast

import pytest
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError

from corpus_structure.semantic.completion_drafts import CompletionDraftStore
from corpus_structure.semantic.data_operation_identity import semantic_value
from corpus_structure.semantic.data_operation_storage import DataOperationStorage
from corpus_structure.semantic.metadata import get_metadata
from corpus_structure.semantic.target_installation import capture_target_installation
from native_test_support import principal_engine
from semantic.data_operation_demand_support import (
    attach,
    cancel_demand,
    claim,
    expire_lease,
    publish,
)
from semantic.data_operation_kernel_support import STORAGE, admit_kernel, prepare_kernel
from semantic.test_target_installation_native import install_target_root


def test_private_native_origin_recovery_preserves_original_and_refuses_unretired(
    semantic_bare_engine,
    native_settings,
    tmp_path,
    monkeypatch,
):
    from corpus_structure.semantic import migrations

    engine = semantic_bare_engine
    epoch = capture_target_installation(get_metadata())
    _, _, _, _, _, location = install_target_root(engine, epoch, tmp_path)
    monkeypatch.setattr(migrations, "ALEMBIC_DIR", location)
    preparation = prepare_kernel(STORAGE, directory=tmp_path / "kernel")
    with engine.begin() as connection:
        kernel = admit_kernel(connection, STORAGE, preparation=preparation)
    writer = principal_engine(native_settings, "write", engine.url.database)
    kernel = replace(kernel, engine=writer)
    try:
        demand, _, _, attached = attach(kernel)
        original = claim(kernel, attached, holder="original")
        with writer.begin() as connection:
            origin = DataOperationStorage(connection).register_data_execution_origin(
                cast(
                    Any,
                    {
                        **original,
                        "runtime_id": kernel.runtime,
                    },
                )
            )
            replay = DataOperationStorage(connection).register_data_execution_origin(
                cast(
                    Any,
                    {
                        **original,
                        "runtime_id": kernel.runtime,
                    },
                )
            )
            assert origin == replay and origin["candidates"] == []
        completion = {
            "outcome": "success",
            "inputs": [],
            "support": [],
            "implementation_revision": "native-test-source-v1",
            "outputs": [
                {
                    "role": "result",
                    "position": 0,
                    "multiplicity": 1,
                    "product": {
                        "kind_contract": kernel.kind,
                        "body": semantic_value(41),
                        "members": [],
                    },
                }
            ],
        }
        store = CompletionDraftStore(tmp_path / "private-drafts", max_bytes=65536)
        draft = store.acknowledge(
            {**original, "runtime_id": kernel.runtime, "completion": completion},
            release_id=kernel.prepared.release_id,
            operation="source.pdf/capture",
            basis=b'{"execution_origin":"' + origin["origin_id"].encode() + b'"}',
            check_active=lambda: None,
        )
        # Successful function evaluation followed by rollback leaves no native
        # intent but must leave the independently acknowledged exact answer.
        with writer.connect() as connection, connection.begin() as transaction:
            DataOperationStorage(connection).retain_data_completion_intent(
                cast(Any, draft.native_request())
            )
            transaction.rollback()
        assert store.open(draft.identity).request == draft.request
        with writer.begin() as connection:
            storage = DataOperationStorage(connection)
            storage.release_data_attempt(
                cast(
                    Any,
                    {
                        **original,
                        "physical_retirement": "confirmed",
                        "failure": {
                            "code": "settlement-rollback",
                            "message": "original producer retired",
                        },
                    },
                )
            )
        cancel_demand(kernel, demand)
        _, _, _, replacement = attach(
            kernel, targets=("urn:ddo-test:source", "urn:ddo-test:consumer")
        )
        adopter = claim(kernel, replacement, holder="adopter")
        assert adopter["generation"] == original["generation"] + 1
        assert adopter["task_id"] != original["task_id"]
        with writer.begin() as connection:
            storage = DataOperationStorage(connection)
            adopted_origin = storage.register_data_execution_origin(
                cast(
                    Any,
                    {
                        **adopter,
                        "runtime_id": kernel.runtime,
                    },
                )
            )
            assert adopted_origin["candidates"] == [
                {
                    "origin_id": origin["origin_id"],
                    "request_id": original["request_id"],
                    "generation": original["generation"],
                }
            ]
            payload = {
                **adopter,
                "origin_id": origin["origin_id"],
                "draft_id": draft.identity,
                "completion": completion,
            }
            intent = storage.consume_data_completion_draft(cast(Any, payload))
            assert storage.consume_data_completion_draft(cast(Any, payload)) == intent
        result = publish(kernel, adopter, intent)
        assert publish(kernel, adopter, intent) == {**result, "replayed": True}
        with writer.connect() as connection:
            inspected = DataOperationStorage(connection).inspect_data_completion(
                cast(
                    Any,
                    {
                        "intent_id": intent["intent_id"],
                        "request_id": adopter["request_id"],
                        "generation": adopter["generation"],
                    },
                )
            )
        assert inspected["state"] == "committed"
        assert inspected["producer_task_id"] == original["task_id"]
        assert inspected["receipt_id"] == result["receipt_id"]
        with engine.connect() as connection:
            row = connection.execute(
                text(
                    "SELECT producer_task_id,producer_attempt,runtime_id,generation FROM ops.data_derivation WHERE id=:id"
                ),
                {"id": result["derivation_id"]},
            ).one()
            assert tuple(row) == (
                original["task_id"],
                original["attempt"],
                kernel.runtime,
                original["generation"],
            )
            receipt = connection.execute(
                text(
                    "SELECT publishing_task_id,publishing_attempt FROM ops.data_publication_receipt WHERE id=:id"
                ),
                {"id": result["receipt_id"]},
            ).one()
            assert tuple(receipt) == (adopter["task_id"], adopter["attempt"])
            assert connection.scalar(text("SELECT count(*) FROM ops.data_draft_consumption")) == 1

        # Lease expiry supplies no physical retirement proof for the original.
        _, _, _, pending = attach(kernel, subject="subject:unretired")
        stale = claim(kernel, pending, holder="stale", seconds=1)
        with writer.begin() as connection:
            unretired_origin = DataOperationStorage(connection).register_data_execution_origin(
                cast(
                    Any,
                    {
                        **stale,
                        "runtime_id": kernel.runtime,
                    },
                )
            )
        expire_lease(replace(kernel, engine=engine), stale)
        current = claim(kernel, pending, holder="current")
        with writer.begin() as connection:
            storage = DataOperationStorage(connection)
            with (
                pytest.raises(DBAPIError, match="original producer retirement"),
                connection.begin_nested(),
            ):
                storage.consume_data_completion_draft(
                    cast(
                        Any,
                        {
                            **current,
                            "origin_id": unretired_origin["origin_id"],
                            "draft_id": sha256(b"unretired").hexdigest(),
                            "completion": completion,
                        },
                    )
                )
            with pytest.raises(DBAPIError), connection.begin_nested():
                storage.consume_data_completion_draft(
                    cast(
                        Any,
                        {
                            **stale,
                            "origin_id": unretired_origin["origin_id"],
                            "draft_id": sha256(b"stale").hexdigest(),
                            "completion": completion,
                        },
                    )
                )
        _assert_native_pdf_material_snapshots(engine, tmp_path / "material-snapshots", monkeypatch)
        _assert_native_pdf_contributor_transfer(
            engine, writer, native_settings, tmp_path / "pdf-contributors"
        )
    finally:
        writer.dispose()


def _assert_native_pdf_material_snapshots(engine, tmp_path, monkeypatch):
    """Persist genuinely prepared archive inputs; compare through installed native owner."""
    import json

    import yaml

    from corpus_structure.semantic import pdf_domain
    from corpus_structure.semantic.pdf_lowering import LOWERING_CONTRACT
    from corpus_structure.semantic.pdf_spool_native import SPOOL_MATERIAL_PREFIX
    from corpus_structure.semantic.releases import persist_release
    from corpus_structure.semantic.types import SourceArtifact
    from semantic.current_pdf_source_support import current_pdf_recipe

    current = pdf_domain.pdf_domain_sources()
    action = next(source for source in current if source.name == "pdf-domain/native/actions.yaml")
    old_action = yaml.safe_load(action.content)
    for declared in old_action["actions"]:
        declared["calls"] = [
            call for call in declared["calls"] if call["id"] != "read_pdf_spool_recovery_candidates"
        ]
    prior = pdf_domain.pdf_domain_sources(
        actions_source=SourceArtifact(action.name, yaml.safe_dump(old_action).encode())
    )

    def change_input(sources, name):
        sources = list(sources)
        position = next(index for index, source in enumerate(sources) if source.name == name)
        sources[position] = SourceArtifact(name, sources[position].content + b"\n")
        lower_index = next(
            index
            for index, source in enumerate(sources)
            if source.name == "pdf-domain/" + LOWERING_CONTRACT
        )
        lower = json.loads(sources[lower_index].content)
        for item in lower["inputs"]:
            if item["name"] == name:
                item["sha256"] = sources[position].digest
        sources[lower_index] = SourceArtifact(sources[lower_index].name, json.dumps(lower).encode())
        declaration = json.loads(sources[0].content)
        declaration["inputs"] = [
            {"name": source.name, "sha256": source.digest} for source in sources[1:]
        ]
        sources[0] = SourceArtifact(sources[0].name, json.dumps(declaration).encode())
        return tuple(sources)

    projections = []
    for index, sources in enumerate(
        (
            prior,
            current,
            change_input(current, SPOOL_MATERIAL_PREFIX + "schema/inline_candidate_pages.json"),
            change_input(current, SPOOL_MATERIAL_PREFIX + "semantic/pdf_certification.py"),
        )
    ):
        with monkeypatch.context() as archive:
            archive.setattr(pdf_domain, "pdf_domain_sources", lambda sources=sources, **_: sources)
            prepared = prepare_kernel(current_pdf_recipe(tmp_path / f"snapshot-{index}"))
            with engine.begin() as connection:
                persist_release(
                    connection,
                    prepared.bundle,
                    prepared.dependencies,
                    prepared.profile,
                    prepared.prepared,
                )
                actual = connection.scalar(
                    text("SELECT ops.pdf_spool_material_identity(:release,:digest)"),
                    {
                        "release": prepared.prepared.release_id,
                        "digest": sources[0].digest,
                    },
                )
                assert actual is not None
                assert (
                    connection.scalar(
                        text("SELECT ops.pdf_spool_material_identity(:release,:digest)"),
                        {
                            "release": prepared.prepared.release_id,
                            "digest": "0" * 64,
                        },
                    )
                    is None
                )
                projections.append(actual)
    assert projections[0] == projections[1]
    assert projections[2] != projections[1]
    assert projections[3] != projections[1]


def _assert_native_pdf_contributor_transfer(engine, writer, native_settings, tmp_path):
    from types import SimpleNamespace

    from corpus_structure.ingest.pdf_build_spool import (
        PdfBuildSpool,
        PdfSpoolPremises,
        PdfSpoolProducerBasis,
        selected_replay_bytes,
    )
    from corpus_structure.ingest.pdf_stream_types import PdfReplayRef
    from corpus_structure.semantic import _pdf_native_calls as calls
    from corpus_structure.semantic.identifiers import RuntimeId, TaskAttempt, TaskId
    from corpus_structure.semantic.pdf_staging import begin_pdf_build
    from semantic.pdf_staging_support import _private_build_factory

    tmp_path.mkdir(parents=True, exist_ok=True)
    admitter = principal_engine(native_settings, "admit", engine.url.database)
    try:
        factory = _private_build_factory(
            engine, writer, tmp_path, SimpleNamespace(param=None), admission_engine=admitter
        )
        original = factory()
        runtime = RuntimeId(factory.kernel.runtime)

        def args(build):
            return dict(
                build_id=build.build_id,
                task_id=TaskId(build.task_id),
                attempt=TaskAttempt(build.attempt),
                holder=build.holder,
                runtime_id=runtime,
            )

        with writer.begin() as connection:
            assert not calls.read_pdf_spool_recovery_candidates(connection, **args(original))
            basis = calls.read_pdf_producer_basis(
                connection,
                task_id=TaskId(original.task_id),
                attempt=TaskAttempt(original.attempt),
                holder=original.holder,
                runtime_id=runtime,
            )
        premises = PdfSpoolPremises(
            PdfSpoolProducerBasis(**basis.model_dump(mode="python")),
            original.source_digest,
            original.recipe_digest,
            original.schema_digest,
            "a" * 64,
            None,
            (("controlled-provider", "1"),),
        )
        old_spool = PdfBuildSpool(
            tmp_path / "spools",
            build_id=original.build_id,
            task_id=original.task_id,
            attempt=original.attempt,
            holder=original.holder,
            check_active=lambda: None,
        )
        try:
            with writer.begin() as connection:
                producer = calls.register_pdf_spool_producer(
                    connection,
                    **args(original),
                    writer_device=old_spool.writer_lease.identity["device"],
                    writer_inode=old_spool.writer_lease.identity["inode"],
                    premises_bytes=premises.to_bytes(),
                )
            old_spool.declare_premises(premises, producer)
            path = old_spool.root / "retained-native"
            path.write_bytes(b"independent exact original bytes")
            replay = PdfReplayRef.from_path(path, "native")
            old_spool.append(replay)
            manifest = old_spool.path.read_bytes()
            selected = selected_replay_bytes(old_spool.root, (replay,))
        finally:
            old_spool.close()
        with writer.begin() as connection:
            DataOperationStorage(connection).release_data_attempt(
                cast(
                    Any,
                    {
                        **factory.requests[original.build_id].fence,
                        "physical_retirement": "confirmed",
                        "failure": {
                            "code": "retired-producer",
                            "message": "original spool writer closed",
                        },
                    },
                )
            )
            reclaimed = factory.reclaim(connection, original, holder="actual-adopter")
            current = begin_pdf_build(
                connection,
                task_id=reclaimed["task_id"],
                attempt=reclaimed["attempt"],
                holder=reclaimed["holder"],
                source_digest=original.source_digest,
                recipe_digest=original.recipe_digest,
                schema_digest=original.schema_digest,
                replay_key="adopt-original-spool",
            )
        assert current.build_id != original.build_id
        with writer.begin() as connection:
            candidates = calls.read_pdf_spool_recovery_candidates(connection, **args(current))
            assert [(row.build_id, row.task_id, row.producer_id) for row in candidates] == [
                (original.build_id, original.task_id, producer)
            ]
            basis = calls.read_pdf_producer_basis(
                connection,
                task_id=TaskId(current.task_id),
                attempt=TaskAttempt(current.attempt),
                holder=current.holder,
                runtime_id=runtime,
            )
        current_premises = replace(
            premises, producer=PdfSpoolProducerBasis(**basis.model_dump(mode="python"))
        )
        with (
            PdfBuildSpool(
                tmp_path / "spools",
                build_id=current.build_id,
                task_id=current.task_id,
                attempt=current.attempt,
                holder=current.holder,
                check_active=lambda: None,
            ) as current_spool,
            writer.begin() as connection,
        ):
            calls.register_pdf_spool_producer(
                connection,
                **args(current),
                writer_device=current_spool.writer_lease.identity["device"],
                writer_inode=current_spool.writer_lease.identity["inode"],
                premises_bytes=current_premises.to_bytes(),
            )
            contributor = calls.register_pdf_spool_contributor(
                connection,
                **args(current),
                producer_id=producer,
                manifest_bytes=manifest,
                selected_replays=selected,
            )
            assert (
                calls.register_pdf_spool_contributor(
                    connection,
                    **args(current),
                    producer_id=producer,
                    manifest_bytes=manifest,
                    selected_replays=selected,
                )
                == contributor
            )
            receipts = calls.read_pdf_spool_contributors(
                connection,
                build_id=current.build_id,
                task_id=TaskId(current.task_id),
                attempt=TaskAttempt(current.attempt),
                holder=current.holder,
            )
            assert receipts[0].producer_id == producer
            assert receipts[0].producer_attempt == original.attempt
            assert receipts[0].adopter_attempt == current.attempt
    finally:
        admitter.dispose()
