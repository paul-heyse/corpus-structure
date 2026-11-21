"""Actual private current-target original execution and adopter correspondence."""

from copy import deepcopy
from dataclasses import replace
from hashlib import sha256
from typing import Any, cast

import pytest
from sqlalchemy import literal, select, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.exc import DBAPIError

from corpus_structure.semantic.completion_drafts import CompletionDraftStore
from corpus_structure.semantic.data_operation_json import json_bytes
from corpus_structure.semantic.data_operation_storage import DataOperationStorage
from corpus_structure.semantic.data_operation_values import semantic_value
from corpus_structure.semantic.data_operation_wire import wire_contracts
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
            writer_schema=json_bytes(wire_contracts()["retain_data_completion_intent"]["input"]),
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
            current_origin = storage.register_data_execution_origin(
                cast(Any, {**current, "runtime_id": kernel.runtime})
            )
            assert current_origin["candidates"] == []
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
        _assert_native_pdf_contributor_transfer(
            engine, writer, native_settings, tmp_path / "pdf-contributors", monkeypatch
        )
    finally:
        writer.dispose()


def test_private_native_pdf_material_snapshots(semantic_bare_engine, tmp_path, monkeypatch):
    from corpus_structure.semantic import migrations

    engine = semantic_bare_engine
    epoch = capture_target_installation(get_metadata())
    _, _, _, _, _, location = install_target_root(engine, epoch, tmp_path)
    monkeypatch.setattr(migrations, "ALEMBIC_DIR", location)
    _assert_native_pdf_material_snapshots(engine, tmp_path / "material-snapshots", monkeypatch)


def _native_lowering_snapshot(sources, *, complete=True):
    """An authored archive fixture for native attribution and compatibility."""
    import json

    from corpus_structure.semantic.pdf_lowering import LOWERING_CONTRACT
    from corpus_structure.semantic.types import SourceArtifact

    values = list(sources)
    index = next(
        i for i, source in enumerate(values) if source.name == "pdf-domain/" + LOWERING_CONTRACT
    )
    contract = json.loads(values[index].content)
    # The fixture does not run a converter or certify real production code.
    # Its explicit completeness premise lets native tests independently vary
    # material, carrier and eligibility records. Real unknown code identity stays
    # covered by the ordinary current-owner contributor test.
    contract["code_identity"] = {
        "complete": complete,
        "sha256": sha256(b"authored native PDF basis").hexdigest() if complete else None,
        "unknowns": [],
    }
    values[index] = SourceArtifact(values[index].name, json.dumps(contract).encode())
    domain = json.loads(values[0].content)
    domain["inputs"] = [{"name": source.name, "sha256": source.digest} for source in values[1:]]
    values[0] = SourceArtifact(values[0].name, json.dumps(domain).encode())
    return tuple(values)


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

    current = _native_lowering_snapshot(pdf_domain.pdf_domain_sources())
    action = next(source for source in current if source.name == "pdf-domain/native/actions.yaml")
    old_action = yaml.safe_load(action.content)
    for declared in old_action["actions"]:
        declared["calls"] = [
            call for call in declared["calls"] if call["id"] != "read_pdf_spool_recovery_candidates"
        ]
    prior = _native_lowering_snapshot(
        pdf_domain.pdf_domain_sources(
            actions_source=SourceArtifact(action.name, yaml.safe_dump(old_action).encode())
        )
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
            change_input(current, SPOOL_MATERIAL_PREFIX + "schema/docling-native.json"),
            change_input(current, SPOOL_MATERIAL_PREFIX + "code/meaning.json"),
            _native_lowering_snapshot(pdf_domain.pdf_domain_sources(), complete=False),
        )
    ):
        with monkeypatch.context() as archive:
            archive.setattr(pdf_domain, "pdf_domain_sources", lambda sources=sources, **_: sources)
            workspace = tmp_path / f"snapshot-{index}"
            prepared = prepare_kernel(current_pdf_recipe(workspace), directory=workspace)
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
                # Exact released attribution works for either completeness bit.
                # The independently authored incomplete archive never establishes
                # transferable material identity.
                assert (actual is not None) == (index != 4)
                # Only the current native basis can supply executable attribution;
                # historical variants above exercise archived material comparison.
                if index in (1, 4):
                    lowering = next(
                        source
                        for source in sources
                        if source.name == "pdf-domain/" + LOWERING_CONTRACT
                    )
                    assert (
                        connection.scalar(
                            text("SELECT ops.pdf_lowering_identity(:release)"),
                            {"release": prepared.prepared.release_id},
                        )
                        == lowering.digest
                    )
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
    assert projections[4] is None


def _assert_native_pdf_contributor_transfer(engine, writer, native_settings, tmp_path, monkeypatch):
    from types import SimpleNamespace

    from corpus_structure.ingest.pdf_build_spool import (
        PdfBuildSpool,
        PdfSpoolPremises,
        PdfSpoolProducerBasis,
        selected_replay_bytes,
    )
    from corpus_structure.ingest.pdf_stream_types import PdfReplayRef
    from corpus_structure.semantic import _pdf_native_calls as calls
    from corpus_structure.semantic.data_operation_demands import OperationSelection
    from corpus_structure.semantic.identifiers import RuntimeId, TaskAttempt, TaskId
    from corpus_structure.semantic.identity import canonical_bytes
    from semantic.pdf_staging_support import _private_build_factory

    tmp_path.mkdir(parents=True, exist_ok=True)
    admitter = principal_engine(native_settings, "admit", engine.url.database)
    try:
        from corpus_structure.semantic import pdf_domain
        from semantic.current_pdf_source_support import current_pdf_recipe

        sources = _native_lowering_snapshot(pdf_domain.pdf_domain_sources())
        with monkeypatch.context() as archive:
            archive.setattr(pdf_domain, "pdf_domain_sources", lambda **_: sources)
            original_recipe = current_pdf_recipe(tmp_path / "owned-recipe")
        original_factory = _private_build_factory(
            engine,
            writer,
            tmp_path,
            SimpleNamespace(param=None),
            admission_engine=admitter,
            kernel_recipe=original_recipe,
        )
        current_factory = original_factory
        operation = "source.pdf/capture"
        assert any(
            not asset.reuse_eligible
            for asset in original_factory.kernel.model.operation(operation).assets
        )
        original = original_factory()
        runtime = RuntimeId(original_factory.kernel.runtime)
        current_runtime = RuntimeId(current_factory.kernel.runtime)

        def args(build, factory):
            return dict(
                build_id=build.build_id,
                task_id=TaskId(build.task_id),
                attempt=TaskAttempt(build.attempt),
                holder=build.holder,
                runtime_id=RuntimeId(factory.kernel.runtime),
            )

        with writer.begin() as connection:
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
        with writer.begin() as connection:
            assert not calls.read_pdf_spool_recovery_candidates(
                connection, **args(original, original_factory), premises_bytes=premises.to_bytes()
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
                    **args(original, original_factory),
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
                        **original_factory.requests[original.build_id].fence,
                        "physical_retirement": "confirmed",
                        "failure": {
                            "code": "retired-producer",
                            "message": "original spool writer closed",
                        },
                    },
                )
            )
        current = current_factory(
            targets=("source.pdf/capture", "source.pdf_views/discovery"),
            selections=(
                OperationSelection(
                    "source.pdf_views/discovery",
                    parameters=canonical_bytes({"sections": [], "membership": "direct"}),
                ),
            ),
        )
        assert current.task_id != original.task_id
        assert (
            current_factory.requests[current.build_id].fence["request_id"]
            != original_factory.requests[original.build_id].fence["request_id"]
        )
        assert current.build_id != original.build_id
        with writer.begin() as connection:
            basis = calls.read_pdf_producer_basis(
                connection,
                task_id=TaskId(current.task_id),
                attempt=TaskAttempt(current.attempt),
                holder=current.holder,
                runtime_id=current_runtime,
            )
        current_premises = replace(
            premises, producer=PdfSpoolProducerBasis(**basis.model_dump(mode="python"))
        )
        with PdfBuildSpool(
            tmp_path / "spools",
            build_id=current.build_id,
            task_id=current.task_id,
            attempt=current.attempt,
            holder=current.holder,
            check_active=lambda: None,
        ) as current_spool:
            with writer.begin() as connection:
                calls.register_pdf_spool_producer(
                    connection,
                    **args(current, current_factory),
                    writer_device=current_spool.writer_lease.identity["device"],
                    writer_inode=current_spool.writer_lease.identity["inode"],
                    premises_bytes=current_premises.to_bytes(),
                )
                candidates = calls.read_pdf_spool_recovery_candidates(
                    connection,
                    **args(current, current_factory),
                    premises_bytes=current_premises.to_bytes(),
                )
            actual = [(row.build_id, row.task_id, row.producer_id) for row in candidates]
            expected = [(original.build_id, original.task_id, producer)]
            diagnosis = (
                actual
                if actual
                else _pdf_recovery_differences(engine, original.build_id, current.build_id)
            )
            assert actual == expected, diagnosis
            _assert_pdf_support_projection(
                engine,
                original.build_id,
                current.build_id,
                args(current, current_factory),
                current_premises.to_bytes(),
            )
            with writer.begin() as connection:
                for incompatible in (
                    replace(current_premises, packages=(("controlled-provider", "2"),)),
                    replace(current_premises, asset_manifest_digest="a" * 64),
                    replace(current_premises, page_range=(2, 3)),
                ):
                    assert (
                        calls.read_pdf_spool_recovery_candidates(
                            connection,
                            **args(current, current_factory),
                            premises_bytes=incompatible.to_bytes(),
                        )
                        == ()
                    )
            different_policy = current_factory(case="unknown-cell-coverage")
            with writer.begin() as connection:
                other_basis = calls.read_pdf_producer_basis(
                    connection,
                    task_id=TaskId(different_policy.task_id),
                    attempt=TaskAttempt(different_policy.attempt),
                    holder=different_policy.holder,
                    runtime_id=current_runtime,
                )
                other_premises = replace(
                    current_premises,
                    producer=PdfSpoolProducerBasis(**other_basis.model_dump(mode="python")),
                )
                assert (
                    calls.read_pdf_spool_recovery_candidates(
                        connection,
                        **args(different_policy, current_factory),
                        premises_bytes=other_premises.to_bytes(),
                    )
                    == ()
                )
            with writer.begin() as connection:
                contributor = calls.register_pdf_spool_contributor(
                    connection,
                    **args(current, current_factory),
                    producer_id=producer,
                    manifest_bytes=manifest,
                    selected_replays=selected,
                )
                assert (
                    calls.register_pdf_spool_contributor(
                        connection,
                        **args(current, current_factory),
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


def _pdf_recovery_differences(engine, original_build, current_build):
    """Bounded failure diagnosis from registered native facts, not an acceptance oracle."""
    import json

    with engine.connect() as connection:
        rows = (
            connection.execute(
                text(
                    "SELECT p.build_id,p.recovery_key,convert_from(p.premises_bytes,'UTF8')::jsonb AS premises,"
                    "o.request_snapshot || jsonb_build_object('subject_definition',"
                    "o.definition_snapshot->'subject_definition') AS request "
                    "FROM ops.pdf_spool_producer p JOIN ops.data_execution_origin o "
                    "ON o.id=p.execution_origin_id WHERE p.build_id IN (:original,:current)"
                ),
                {"original": original_build, "current": current_build},
            )
            .mappings()
            .all()
        )
    by_build = {row["build_id"]: row for row in rows}
    old, new = by_build[original_build], by_build[current_build]

    def differences(before, after):
        return {
            name: [before.get(name), after.get(name)]
            for name in before.keys() | after.keys()
            if before.get(name) != after.get(name)
        }

    fields = (
        "project_id",
        "operation_id",
        "subject",
        "subject_definition",
        "original_source",
        "analyzed_scope",
        "replicate",
    )
    binding = (
        "inputs",
        "support",
        "parameters",
        "request_inputs",
        "inference",
        "execution_profile",
        "populations",
    )
    return json.dumps(
        {
            "recovery_keys": [old["recovery_key"], new["recovery_key"]],
            "premises": differences(old["premises"], new["premises"]),
            "projection": differences(old["material"] or {}, new["material"] or {}),
            "request": differences(
                {name: old["request"].get(name) for name in fields},
                {name: new["request"].get(name) for name in fields},
            ),
            "binding": differences(
                {name: old["request"]["binding"].get(name) for name in binding},
                {name: new["request"]["binding"].get(name) for name in binding},
            ),
        }
    )


def _assert_pdf_support_projection(engine, original_build, current_build, current_args, premises):
    """Authenticate actual original admissions; retain slot and other support meaning."""
    import json
    from copy import deepcopy

    from corpus_structure.semantic import _pdf_native_calls as calls

    with engine.connect() as connection:
        snapshots = dict(
            connection.execute(
                text(
                    "SELECT p.build_id,o.request_snapshot || jsonb_build_object('subject_definition',"
                    "o.definition_snapshot->'subject_definition') FROM ops.pdf_spool_producer p "
                    "JOIN ops.data_execution_origin o ON o.id=p.execution_origin_id "
                    "WHERE p.build_id IN (:original,:current)"
                ),
                {"original": original_build, "current": current_build},
            ).all()
        )

    def projected(connection, snapshot):
        return connection.scalar(
            text("SELECT ops.pdf_spool_request_material(CAST(:snapshot AS jsonb))"),
            {"snapshot": json.dumps(snapshot)},
        )

    original, current = snapshots[original_build], snapshots[current_build]
    with engine.connect() as connection:
        baseline = projected(connection, original)
        assert baseline is not None and baseline == projected(connection, current)
        assert (
            original["binding"]["support"][0]["admission_id"]
            != (current["binding"]["support"][0]["admission_id"])
        )
        for field, value in (
            ("admission_id", "original-admission:absent"),
            ("source_reference", "0" * 64),
        ):
            altered = deepcopy(original)
            altered["binding"]["support"][0][field] = value
            assert projected(connection, altered) is None
        altered = deepcopy(original)
        altered["project_id"] = "another-project"
        assert projected(connection, altered) is None
        for field, value in (("role", "another-role"), ("position", 1)):
            altered = deepcopy(original)
            altered["binding"]["support"][0][field] = value
            assert projected(connection, altered) != baseline
        altered = deepcopy(original)
        opaque = {
            "kind": "computation",
            "role": "another",
            "position": 1,
            "derivation_id": "episode:exact",
        }
        altered["binding"]["support"].append(opaque)
        assert projected(connection, altered)["binding"]["support"][-1] == opaque

    # Real revocations separately invalidate prior and current authorization. The
    # protected immutable rows remain intact; each native effect is rolled back.
    for snapshot in (original, current):
        with engine.connect() as connection, connection.begin() as transaction:
            DataOperationStorage(connection).revoke_data_support(
                cast(
                    Any,
                    {
                        "project_id": snapshot["project_id"],
                        "original_source": snapshot["original_source"],
                        "selector_kind": "original-admission",
                        "selector": snapshot["binding"]["support"][0]["admission_id"],
                        "reason": "independent PDF support revocation control",
                    },
                )
            )
            assert projected(connection, snapshot) is None
            if snapshot is original:
                assert (
                    calls.read_pdf_spool_recovery_candidates(
                        connection,
                        **current_args,
                        premises_bytes=premises,
                    )
                    == ()
                )
            else:
                with pytest.raises(DBAPIError), connection.begin_nested():
                    calls.read_pdf_spool_recovery_candidates(
                        connection,
                        **current_args,
                        premises_bytes=premises,
                    )
            transaction.rollback()


@pytest.mark.db
@pytest.mark.parametrize(
    ("change", "expected"),
    [
        ("unchanged", True),
        ("key", True),
        ("transport", True),
        ("project", False),
        ("operation", False),
        ("recipe", False),
        ("source", False),
        ("scope", False),
        ("replicate", False),
        ("support", False),
        ("parameters", False),
        ("implementation", False),
        ("output", False),
        ("unknown-key", False),
        ("missing-eligibility-key", False),
    ],
)
def test_native_draft_material_compares_the_producer_basis(native_read, change, expected):
    from corpus_structure.semantic.execution_origin_native import completion_material_matches

    original: dict[str, Any] = {
        "request_key": "request:original",
        "project_id": "project:one",
        "operation_id": "operation:one",
        "recipe": "recipe:one",
        "subject": "subject:one",
        "original_source": "source:one",
        "analyzed_scope": {"page": 1},
        "replicate": None,
        "binding": {
            "inputs": [],
            "support": [],
            "parameters": {},
            "request_inputs": {},
            "inference": "inference:one",
            "execution_profile": "profile:one",
            "populations": [],
        },
    }
    definition: dict[str, Any] = {
        "implementation_revision": "implementation:one",
        "profile": "profile:one",
        "output_roles": [{"name": "result"}],
        "support_contract": {"reuse_eligible": True},
    }
    current = deepcopy(original)
    current_definition = deepcopy(definition)
    if change == "key":
        current["request_key"] = "request:other"
    elif change == "transport":
        current.update(runtime_id="runtime:other", generation=2, release_id="release:other")
    elif change in {"project", "operation", "recipe", "source", "replicate"}:
        field = {
            "project": "project_id",
            "operation": "operation_id",
            "source": "original_source",
        }.get(change, change)
        current[field] = change + ":other"
    elif change == "scope":
        current["analyzed_scope"] = {"page": 2}
    elif change in {"support", "parameters"}:
        current["binding"][change] = {"changed": True}
    elif change == "implementation":
        current_definition["implementation_revision"] = "implementation:other"
    elif change == "output":
        current_definition["output_roles"] = [{"name": "other"}]
    elif change == "unknown-key":
        definition["support_contract"]["reuse_eligible"] = False
        current_definition["support_contract"]["reuse_eligible"] = False
        current["request_key"] = "request:other"
    elif change == "missing-eligibility-key":
        definition["support_contract"] = {}
        current_definition["support_contract"] = {}
        current["request_key"] = "request:other"
    inputs = select(
        literal(original, type_=JSONB()).label("prior_request"),
        literal(definition, type_=JSONB()).label("prior_definition"),
        literal(current, type_=JSONB()).label("current_request"),
        literal(current_definition, type_=JSONB()).label("current_definition"),
    ).subquery("material_inputs")
    matches = completion_material_matches(
        inputs.c.prior_request,
        inputs.c.prior_definition,
        inputs.c.current_request,
        inputs.c.current_definition,
    )
    assert native_read.scalar(select(matches)) is expected
