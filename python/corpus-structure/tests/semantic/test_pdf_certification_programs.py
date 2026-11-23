"""Generated certification programs retain native privileges and byte framing."""

from types import SimpleNamespace
from typing import TypedDict

import pytest
from native_refusals import native_refusal
from pglast import ast, parse_sql
from pglast.stream import RawStream
from sqlalchemy import Column, MetaData, Table, func, select, text
from sqlalchemy.schema import CreateTable

from corpus_structure.semantic.metadata import get_metadata
from corpus_structure.semantic.native_objects import execute_native_sql, native_owner
from corpus_structure.semantic.pdf_certification_native import pdf_certification_native_sql
from corpus_structure.semantic.pdf_record_identity import IdentityFold, record_frame
from semantic.pdf_staging_support import create_private_build as create_private_build


class StreamFixture(TypedDict):
    product_id: str
    revision_id: str
    stream_id: str
    byte_length: int
    byte_root: str
    encoding_profile: str
    serialization_sha256: str | None


@pytest.mark.parametrize(
    "prior_state",
    ["hit", "failed", "unpublished", "unvalidated", "other-kind", "other-lowering", "forced"],
)
def test_oracle_reuse_requires_passed_published_validated_matching_producer(
    create_private_build, commit_writer_engine, commit_db_engine, tmp_path, prior_state
):
    from pdf_acceptance_support import stage_complete_native

    from corpus_structure.semantic import _pdf_native_calls as calls
    from corpus_structure.semantic.pdf_publication import (
        freeze_pdf_build,
        inspect_pdf_execution_receipt,
        prepare_pdf_build,
        seal_pdf_build,
        validate_pdf_build,
    )

    prior = create_private_build()
    # This is independent retained input data, not the native reuse predicate.
    # An incomplete capture can attest its own exact output; it cannot qualify
    # a different producer by borrowing this producer's oracle.
    import json

    with commit_db_engine.connect() as connection:
        lowering = json.loads(
            connection.scalar(
                text(
                    "SELECT content FROM sem.input WHERE release_id=:release "
                    "AND input_name='pdf-domain/implementation/pdf/lowering-contract.json'"
                ),
                {"release": prior.release_id},
            )
        )
    complete = lowering["code_identity"]["complete"]
    assert type(complete) is bool
    directory = tmp_path / "prior-certified"
    directory.mkdir()
    with create_private_build.maintained(prior):
        stage_complete_native(commit_writer_engine, prior, directory)
        with commit_writer_engine.begin() as connection:
            frozen_prior = freeze_pdf_build(connection, prior, kind="native")
            prepare_pdf_build(connection, frozen_prior)
        validate_pdf_build(commit_writer_engine, frozen_prior, force_oracle=True)
        with commit_db_engine.connect() as connection:
            receipt = connection.scalar(
                text(
                    "SELECT oracle_receipt_id FROM ops.pdf_roundtrip_oracle WHERE build_id=:build AND state='passed'"
                ),
                {"build": prior.build_id},
            )
        assert receipt is not None
        if prior_state != "unpublished":
            with commit_writer_engine.begin() as connection:
                seal_pdf_build(connection, frozen_prior)
        if prior_state in {"failed", "unvalidated", "other-kind", "other-lowering"}:
            with commit_db_engine.begin() as connection:
                # Deliberately corrupt one prior determinant on the owned clone. The next
                # transaction restores normal trigger posture before qualification is read.
                connection.exec_driver_sql("SET LOCAL session_replication_role=replica")
                if prior_state == "failed":
                    connection.execute(
                        text(
                            "UPDATE ops.pdf_roundtrip_oracle SET state='failed',actual_native_digest=NULL WHERE oracle_receipt_id=:receipt"
                        ),
                        {"receipt": receipt},
                    )
                elif prior_state == "unvalidated":
                    connection.execute(
                        text("DELETE FROM ops.pdf_build_validation WHERE build_id=:build"),
                        {"build": prior.build_id},
                    )
                elif prior_state == "other-kind":
                    connection.execute(
                        text(
                            "UPDATE ops.pdf_roundtrip_oracle SET kind='integrated' WHERE oracle_receipt_id=:receipt"
                        ),
                        {"receipt": receipt},
                    )
                    connection.execute(
                        text(
                            "UPDATE ops.pdf_published_revision SET kind='integrated' WHERE build_id=:build"
                        ),
                        {"build": prior.build_id},
                    )
                else:
                    connection.execute(
                        text(
                            "UPDATE ops.pdf_roundtrip_oracle SET lowering_identity='authored-other-lowering' WHERE oracle_receipt_id=:receipt"
                        ),
                        {"receipt": receipt},
                    )

        current = create_private_build(case="unknown-cell-coverage")
        current_directory = tmp_path / "current-certified"
        current_directory.mkdir()
        with create_private_build.maintained(current):
            stage_complete_native(commit_writer_engine, current, current_directory)
            with commit_writer_engine.begin() as connection:
                frozen = freeze_pdf_build(connection, current, kind="native")
                prepare_pdf_build(connection, frozen)
                requirement = calls.read_pdf_certification_requirement(
                    connection,
                    build_id=current.build_id,
                    task_id=current.task_id,
                    attempt=current.attempt,
                    holder=current.holder,
                    frozen_digest=frozen.frozen_digest,
                )
            assert requirement.oracle_receipt_id == (
                receipt if complete and prior_state in {"hit", "forced"} else None
            )
            assert requirement.certification_basis == "producer-certified"
            validate_pdf_build(commit_writer_engine, frozen, force_oracle=prior_state == "forced")
            with commit_writer_engine.begin() as connection:
                publication = seal_pdf_build(connection, frozen)
                execution = inspect_pdf_execution_receipt(
                    connection, publication, attempt=current.attempt, holder=current.holder
                )
            with commit_db_engine.connect() as connection:
                states = list(
                    connection.scalars(
                        text(
                            "SELECT state FROM ops.pdf_roundtrip_oracle WHERE build_id=:build ORDER BY oracle_receipt_id"
                        ),
                        {"build": current.build_id},
                    )
                )
            reused = complete and prior_state == "hit"
            assert states == ([] if reused else ["passed"])
            assert execution.certification.basis == (
                "producer-certified" if reused else "round-trip-verified"
            )


def test_installed_certification_entrypoints_require_exact_writer_fence(
    create_private_build, commit_writer_engine, commit_db_engine, tmp_path
):
    from pdf_acceptance_support import stage_complete_native

    from corpus_structure.semantic import _pdf_native_calls as calls
    from corpus_structure.semantic.pdf_publication import freeze_pdf_build

    build = create_private_build()
    with create_private_build.maintained(build):
        stage_complete_native(commit_writer_engine, build, tmp_path)
        fence = dict(
            build_id=build.build_id,
            task_id=build.task_id,
            attempt=build.attempt,
            holder=build.holder,
        )
        with commit_db_engine.connect() as connection:
            certification = (
                connection.execute(
                    text("SELECT * FROM ops.pdf_producer_certification WHERE build_id=:build"),
                    {"build": build.build_id},
                )
                .mappings()
                .one()
            )
            privileged = (
                (
                    "pdf_lowering_identity",
                    text("SELECT ops.pdf_lowering_identity(:release, :task)"),
                    {"release": build.release_id, "task": build.task_id},
                    certification["lowering_identity"],
                ),
                (
                    "pdf_producer_stream_identity",
                    text("SELECT ops.pdf_producer_stream_identity(:build,:schema)"),
                    {"build": build.build_id, "schema": build.schema_digest},
                    None,
                ),
            )
            for _name, statement, arguments, expected in privileged:
                actual = connection.scalar(statement, arguments)
                if expected is None:
                    # Streams remain private before prepare. The positive control owns
                    # permission to invoke the helper, not staging/copy correspondence.
                    assert isinstance(actual, str) and len(actual) == 64
                else:
                    assert actual == expected
        with commit_writer_engine.begin() as connection:
            for name, statement, arguments, _expected in privileged:
                with (
                    native_refusal("42501", message=f"permission denied for function {name}"),
                    connection.begin_nested(),
                ):
                    connection.execute(statement, arguments)

            def record(holder: str):
                return calls.record_pdf_producer_certification(
                    connection,
                    build_id=build.build_id,
                    task_id=build.task_id,
                    attempt=build.attempt,
                    holder=holder,
                    lowering_identity=certification["lowering_identity"],
                    kind=certification["kind"],
                    logical_digest=certification["logical_digest"],
                    native_document_digest=certification["native_document_digest"],
                    stream_inventory_digest=certification["stream_inventory_digest"],
                )

            def targets(holder: str):
                return calls.read_pdf_certification_targets(
                    connection, **{**fence, "holder": holder}, targets=[]
                )

            record(build.holder)
            assert targets(build.holder) == b"[]"
            for invoke in (record, targets):
                with (
                    native_refusal(
                        "P0004", message="stale private PDF build owner/capability/support"
                    ),
                    connection.begin_nested(),
                ):
                    invoke("authored-stale-holder")

            frozen = freeze_pdf_build(connection, build, kind="native")
            frozen_args = {**fence, "frozen_digest": frozen.frozen_digest}

            def require(holder: str):
                return calls.read_pdf_certification_requirement(
                    connection, **{**frozen_args, "holder": holder}
                )

            def begin(holder: str):
                return calls.begin_pdf_roundtrip_oracle(
                    connection, **{**frozen_args, "holder": holder}
                )

            requirement = require(build.holder)
            assert requirement.oracle_receipt_id is None
            oracle = begin(build.holder)
            assert oracle
            finish_args = {
                **frozen_args,
                "oracle_receipt_id": oracle,
                "state": "interrupted",
                "actual_native_digest": None,
                "error_message": "authored interrupted oracle control",
            }

            def finish(holder: str):
                return calls.finish_pdf_roundtrip_oracle(
                    connection, **{**finish_args, "holder": holder}
                )

            finish(build.holder)
            for invoke, reason in (
                (require, "stale frozen PDF owner"),
                (begin, "stale private PDF build owner/capability/support"),
                (finish, "stale frozen PDF owner"),
            ):
                with native_refusal("P0004", message=reason), connection.begin_nested():
                    invoke("authored-stale-holder")
            with (
                native_refusal(
                    "P0002",
                    message="query returned no rows",
                    context="ops.finish_pdf_roundtrip_oracle",
                ),
                connection.begin_nested(),
            ):
                calls.finish_pdf_roundtrip_oracle(
                    connection, **{**finish_args, "oracle_receipt_id": "authored-absent-receipt"}
                )
        with commit_db_engine.connect() as connection:
            assert connection.execute(
                text(
                    "SELECT state,error_message FROM ops.pdf_roundtrip_oracle WHERE build_id=:build"
                ),
                {"build": build.build_id},
            ).all() == [("interrupted", "authored interrupted oracle control")]


def test_native_lowering_authenticates_selected_scope_and_keeps_v2_certification(native_rollback):
    import json
    from hashlib import sha256

    from corpus_structure.semantic.pdf_certification_native import pdf_certification_native_programs
    from corpus_structure.semantic.pdf_domain import pdf_domain_sources
    from corpus_structure.semantic.pdf_domain_native import pdf_domain_native_programs
    from corpus_structure.semantic.pdf_spool_native import pdf_spool_native_programs
    from corpus_structure.semantic.types import SourceArtifact

    model = get_metadata()
    tasks, requests = (
        Table(
            fixture_name,
            MetaData(),
            *(Column(field.name, field.type) for field in model.tables[model_name].c),
            schema="pg_temp",
        )
        for model_name, fixture_name in (
            ("ops.task", "certification_tasks"),
            ("ops.data_request", "certification_requests"),
        )
    )
    fixture = Table(
        "certification_archive",
        MetaData(),
        *(
            Column(column.name, column.type, nullable=column.nullable)
            for column in model.tables["sem.input"].c
        ),
        schema="pg_temp",
    )
    supplied = SimpleNamespace(
        tables={
            **model.tables,
            "sem.input": fixture,
            "ops.data_request": requests,
            "ops.task": tasks,
        }
    )
    contract, *baseline = pdf_domain_sources(include_producer=False)
    material = tuple(
        source
        for source in baseline
        if source.name
        in {
            "pdf-domain/implementation/pdf/lowering/schema/docling-native.json",
            "pdf-domain/implementation/pdf/lowering/codec/inline-candidates.arrow",
        }
    )
    assert len(material) == 2
    implementation_bytes = b'{"selected":"fixture"}'
    selected = {
        "complete": True,
        "sha256": sha256(implementation_bytes).hexdigest(),
        "scope": "docling-standard-pdf-stream-v1",
    }
    generic = {"complete": False, "sha256": None}

    def lowering_sources(version, code, *, scoped=False):
        # Independently authored inventory names exercise the archived native ABI.
        path = "pdf-domain/implementation/pdf/"
        code_path = "lowering/capture-code/meaning.json" if scoped else "lowering/code/meaning.json"
        contract_path = "lowering/capture-contract.json" if scoped else "lowering-contract.json"
        implementation = SourceArtifact(path + code_path, implementation_bytes)
        lowering = SourceArtifact(
            path + contract_path,
            json.dumps(
                {
                    "profile": f"pdf-record-lowering-contract-{version}",
                    "compiler_policy": "fixture",
                    "code_identity": code,
                    "inputs": [
                        {"name": source.name, "sha256": source.digest}
                        for source in (implementation, *material)
                    ],
                    "libraries": {"fixture": "1"},
                }
            ).encode(),
        )
        return implementation, lowering

    def archived(release, *lowering):
        sources = [*baseline, *(item for basis in lowering for item in basis)]
        document = json.loads(contract.content)
        document["inputs"] = [{"name": source.name, "sha256": source.digest} for source in sources]
        archive = SourceArtifact(contract.name, json.dumps(document).encode())
        sources.append(archive)
        connection.execute(
            fixture.insert(),
            [
                {
                    "release_id": release,
                    "input_kind": "dependency",
                    "input_name": source.name,
                    "content": source.content,
                    "content_digest": source.digest,
                }
                for source in sources
            ],
        )
        return archive.digest

    def task(task_id, release, operation):
        request_id = "req:" + str(task_id)
        connection.execute(requests.insert().values(id=request_id, operation_id=operation))
        connection.execute(
            tasks.insert().values(id=task_id, data_request_id=request_id, release_id=release)
        )

    connection = native_rollback.connection
    archive_reader = next(
        program
        for program in pdf_domain_native_programs(target_metadata=supplied)
        if program.routine.name == "pdf_contract_input"
    )
    lowering = next(
        program
        for program in pdf_certification_native_programs(target_metadata=supplied)
        if program.routine.name == "pdf_lowering_identity"
    )
    spool_programs = {
        program.routine.name: program
        for program in pdf_spool_native_programs(target_metadata=supplied)
    }
    v2 = lowering_sources("v2", generic)
    legacy_v3 = lowering_sources("v3", selected)
    v3 = lowering_sources("v3", selected, scoped=True)
    with native_owner(connection, "corpus_sem_publisher"):
        for table in (fixture, tasks, requests):
            connection.execute(CreateTable(table))
        execute_native_sql(connection, archive_reader.routine.render())
        for name in ("pdf_lowering_contract_name", "pdf_spool_material_identity"):
            execute_native_sql(connection, spool_programs[name].routine.render())
        execute_native_sql(connection, lowering.routine.render())
        archived("previous", v2)
        legacy_archive = archived("old-selected", legacy_v3)
        mixed_archive = archived("mixed", v2, v3)
        task(1, "previous", "source.pdf/capture")
        task(2, "mixed", "source.pdf/capture")
        task(3, "mixed", "source.pdf_sections/organize")
        task(4, "old-selected", "source.pdf/capture")
        for task_id, release, bad_code in (
            (5, "wrong-scope", {**selected, "scope": "unrelated"}),
            (6, "incomplete", {**selected, "complete": False, "sha256": None}),
            (7, "wrong-code", {**selected, "sha256": "0" * 64}),
        ):
            archived(release, v2, lowering_sources("v3", bad_code, scoped=True))
            task(task_id, release, "source.pdf/capture")

    def lowered(release, *origin):
        return select(func.ops.pdf_lowering_identity(release, *origin))

    assert connection.scalar(lowered("previous")) == v2[1].digest
    assert connection.scalar(lowered("previous", 1)) == v2[1].digest
    assert connection.scalar(lowered("mixed")) == v2[1].digest
    assert connection.scalar(lowered("mixed", 2)) == v3[1].digest
    assert connection.scalar(lowered("mixed", 3)) == v2[1].digest
    assert connection.scalar(lowered("old-selected", 4)) == legacy_v3[1].digest

    def recovery_material(release, digest, task_id):
        return connection.scalar(
            select(func.ops.pdf_spool_material_identity(release, digest, task_id))
        )

    # Old and scoped archives identify exactly the same selected code and codecs.
    # The organizing task may not borrow that Standard capture standing.
    expected_material = recovery_material("old-selected", legacy_archive, 4)
    assert expected_material is not None
    assert recovery_material("mixed", mixed_archive, 2) == expected_material
    assert recovery_material("mixed", mixed_archive, 3) is None

    for query, message in (
        (lowered("old-selected"), "unsupported released PDF lowering contract"),
        (lowered("mixed", 1), "PDF lowering requires its exact originating task"),
        (lowered("wrong-scope", 5), "unsupported released PDF lowering contract"),
        (lowered("incomplete", 6), "unsupported released PDF lowering contract"),
        (lowered("wrong-code", 7), "selected PDF producer identity differs from its captured code"),
    ):
        with native_refusal("23514", message=message), connection.begin_nested():
            connection.execute(query)


def test_generated_stream_inventory_matches_independent_python_frames(native_rollback):
    source = get_metadata().tables["ops.pdf_artifact_stream"]
    fixture = Table(
        "certification_streams",
        MetaData(),
        *(Column(column.name, column.type, nullable=column.nullable) for column in source.c),
        schema="pg_temp",
    )
    supplied = SimpleNamespace(tables={**get_metadata().tables, "ops.pdf_artifact_stream": fixture})
    declaration = next(
        item.stmt
        for item in parse_sql(pdf_certification_native_sql(target_metadata=supplied))
        if isinstance(item.stmt, ast.CreateFunctionStmt)
        and item.stmt.funcname
        and item.stmt.funcname[-1].sval == "pdf_producer_stream_identity"
    )
    connection = native_rollback.connection
    rows: list[StreamFixture] = [
        {
            "product_id": "owned",
            "revision_id": "owned",
            "stream_id": "z-stream",
            "byte_length": 19,
            "byte_root": "a" * 64,
            "encoding_profile": "profile-z",
            "serialization_sha256": None,
        },
        {
            "product_id": "owned",
            "revision_id": "owned",
            "stream_id": "a-stream",
            "byte_length": 0,
            "byte_root": "b" * 64,
            "encoding_profile": "profile-a",
            "serialization_sha256": "c" * 64,
        },
        {
            "product_id": "owned",
            "revision_id": "owned",
            "stream_id": "á-stream",
            "byte_length": 7,
            "byte_root": "d" * 64,
            "encoding_profile": "profile-unicode",
            "serialization_sha256": "e" * 64,
        },
    ]
    with native_owner(connection, "corpus_sem_publisher"):
        connection.execute(CreateTable(fixture))
        connection.execute(fixture.insert(), [*rows, {**rows[0], "product_id": "another"}])
        execute_native_sql(connection, RawStream()(declaration))
    folded = IdentityFold("pdf-producer-streams-v1")
    for row in sorted(rows, key=lambda row: row["stream_id"].encode("utf-8")):
        folded.add(
            record_frame(
                "schema-control",
                "producer-stream",
                row["stream_id"],
                (
                    (name, row[name])
                    for name in (
                        "byte_length",
                        "byte_root",
                        "encoding_profile",
                        "serialization_sha256",
                    )
                ),
            )
        )
    assert (
        connection.scalar(text("SELECT ops.pdf_producer_stream_identity('owned','schema-control')"))
        == folded.digest().hex()
    )
    assert (
        connection.scalar(
            text("SELECT ops.pdf_producer_stream_identity('absent','schema-control')")
        )
        == IdentityFold("pdf-producer-streams-v1").digest().hex()
    )
