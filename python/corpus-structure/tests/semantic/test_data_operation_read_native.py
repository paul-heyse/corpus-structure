"""Actual PostgreSQL reply custody and actual-member body authorization controls."""

from hashlib import sha256
from typing import Any

import pytest
from sqlalchemy import Text, text
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.exc import DBAPIError

from corpus_structure.semantic.data_operation_identity import semantic_value
from corpus_structure.semantic.data_operation_read_native import (
    _body_access_programs,
    _cpu_reply_program,
)
from corpus_structure.semantic.identity import canonical_bytes
from corpus_structure.semantic.metadata import metadata
from corpus_structure.semantic.native_objects import execute_native_sql, native_owner


@pytest.mark.parametrize("change", ["none", "digest", "duplicate", "not-string", "not-object"])
def test_program_cpu_reply_preserves_exact_utf8_receipt_and_declared_object(
    infrastructure_rollback, change
):
    reply = "[1,2]" if change == "not-object" else '{"text":"λ","value":7}'
    digest = sha256(reply.encode()).hexdigest()
    evidence: dict[str, Any] = dict(cpu_replies=[reply], cpu_receipts=[dict(result_digest=digest)])
    if change == "digest":
        evidence["cpu_receipts"][0]["result_digest"] = "f" * 64
    elif change == "duplicate":
        evidence["cpu_replies"].append(reply)
    elif change == "not-string":
        evidence["cpu_replies"] = [dict(value=7)]
    connection = infrastructure_rollback
    connection.exec_driver_sql("CREATE SCHEMA ops")
    execute_native_sql(connection, _cpu_reply_program())

    def read():
        return connection.scalar(
            text("SELECT ops.ddo_cpu_reply_value(CAST(:completion AS jsonb))"),
            {"completion": canonical_bytes(dict(execution_evidence=evidence)).decode()},
        )

    if change == "none":
        assert read() == {"text": "λ", "value": 7}
    else:
        message = (
            "declared object result"
            if change == "not-object"
            else "original execution receipt"
            if change == "digest"
            else "actual CPU reply and original receipt"
        )
        with pytest.raises(DBAPIError, match=message) as caught, connection.begin_nested():
            read()
        assert getattr(caught.value.orig, "sqlstate", None) == "23514"


def _body_fixture(connection):
    for name, universe, nominal, contracts in (
        ("container", "ordinary", True, ["kind:ordinary", "kind:reference", "kind:nested"]),
        ("nested", "ordinary", True, ["kind:ordinary", "kind:reference"]),
        ("ordinary", "ordinary", False, []),
        ("reference", "evaluator", False, []),
    ):
        connection.execute(
            insert(metadata.tables["sem.data_kind_contract"]).values(
                kind_contract="kind:" + name,
                kind="literal:" + name,
                body_schema={"type": "object" if nominal else "integer"},
                meaning_schema={"type": "array"},
                member_schema={} if nominal else {"not": {}},
                member_contracts=contracts,
                families=[],
                universe=universe,
            )
        )
    for program in _body_access_programs(metadata):
        execute_native_sql(connection, program)


def _packet(kind, body):
    return dict(kind_contract="kind:" + kind, body=body)


@pytest.mark.parametrize("case", ["ordinary", "protected", "nested", "duplicate"])
def test_program_actual_member_closure_preserves_order_and_purpose(native_rollback, case):
    connection = native_rollback.connection
    _body_fixture(connection)
    packets = [_packet("ordinary", 7)]
    expected = ["kind:container", "kind:ordinary"]
    if case == "protected":
        packets.append(_packet("reference", 9))
        expected.append("kind:reference")
    elif case == "nested":
        packets.append(_packet("nested", dict(members=[_packet("reference", 9)])))
        expected.extend(("kind:nested", "kind:reference"))
    elif case == "duplicate":
        packets.append(_packet("ordinary", 8))
        expected.append("kind:ordinary")
    body = canonical_bytes(semantic_value(dict(members=packets))).decode()
    assert (
        list(
            connection.scalars(
                text(
                    "SELECT * FROM ops.ddo_body_kind_contracts('kind:container',CAST(:body AS jsonb))"
                ),
                {"body": body},
            )
        )
        == expected
    )
    # Normal selected readers invoke this private guard internally. Lend only
    # its entry point in this rollback fixture to isolate the retained caller's
    # universe decision; the production helper remains private.
    connection.exec_driver_sql(
        "GRANT EXECUTE ON FUNCTION ops.ddo_body_access(text,jsonb) TO corpus_sem_writer,corpus_sem_evaluator"
    )
    with native_owner(connection, "corpus_sem_writer"):
        if case in ("protected", "nested"):
            with (
                pytest.raises(
                    DBAPIError, match="evaluator data requires evaluator purpose"
                ) as caught,
                connection.begin_nested(),
            ):
                connection.scalar(
                    text("SELECT ops.ddo_body_access('kind:container',CAST(:body AS jsonb))"),
                    {"body": body},
                )
            assert getattr(caught.value.orig, "sqlstate", None) == "42501"
        else:
            assert (
                connection.scalar(
                    text("SELECT ops.ddo_body_access('kind:container',CAST(:body AS jsonb))"),
                    {"body": body},
                )
                is True
            )
    with native_owner(connection, "corpus_sem_evaluator"):
        assert (
            connection.scalar(
                text("SELECT ops.ddo_body_access('kind:container',CAST(:body AS jsonb))"),
                {"body": body},
            )
            is True
        )


@pytest.mark.parametrize("case", ["unlisted", "wrong-body"])
def test_program_member_cannot_change_nominal_kind_or_schema(native_rollback, case):
    connection = native_rollback.connection
    _body_fixture(connection)
    body = semantic_value(
        dict(
            members=[
                _packet(
                    "unlisted" if case == "unlisted" else "reference",
                    7 if case == "unlisted" else "not an integer",
                )
            ]
        )
    )
    with (
        pytest.raises(
            DBAPIError,
            match="outside its captured nominal contract"
            if case == "unlisted"
            else "differs from its captured nominal kind",
        ),
        connection.begin_nested(),
    ):
        list(
            connection.scalars(
                text(
                    "SELECT * FROM ops.ddo_body_kind_contracts('kind:container',CAST(:body AS jsonb))"
                ),
                {"body": canonical_bytes(body).decode()},
            )
        )


@pytest.mark.parametrize("case", ["missing-read", "foreign-read", "operation", "source-shape"])
def test_program_binding_requires_exact_read_and_frozen_operation_before_projection(
    infrastructure_rollback, case
):
    """Bare current columns isolate refusals before any selected-body query."""
    from sqlalchemy import cast, func
    from sqlalchemy.schema import CreateTable

    from corpus_structure.semantic.data_operation_read_native import _binding_programs

    demand = metadata.tables["ops.data_demand"]
    read = metadata.tables["ops.data_demand_read"]
    connection = infrastructure_rollback
    connection.exec_driver_sql("CREATE SCHEMA ops")
    for relation in (demand, read):
        connection.execute(CreateTable(relation, include_foreign_key_constraints=[]))
    connection.execute(
        insert(demand).values(
            id="demand:literal",
            project_id="project:literal",
            release_id="release:literal",
            runtime_id="runtime:literal",
            root={},
            selection={"operations": [{"operation": "literal:consumer"}]},
            strength="value",
            created_at=func.clock_timestamp(),
        )
    )
    connection.execute(
        insert(read).values(
            id="read:literal",
            demand_id="demand:literal",
            read_snapshot=cast(func.pg_current_snapshot(), Text()),
            frontier_at=func.clock_timestamp(),
            owner_xid=cast(func.pg_current_xact_id(), Text()),
            trust_snapshot={},
            scope=[],
        )
    )
    for program in _binding_programs(metadata):
        execute_native_sql(connection, program)
    query = text(
        "SELECT * FROM ops.ddo_binding_rows('demand:literal',:operation,'{}'::jsonb,:read,NULL,CAST(:source AS jsonb),NULL,true,NULL,true)"
    )
    values = dict(
        operation="foreign:operation" if case == "operation" else "literal:consumer",
        read=None
        if case == "missing-read"
        else "read:foreign"
        if case == "foreign-read"
        else "read:literal",
        source="[]" if case == "source-shape" else None,
    )
    expected = (
        "exact native read acquisition"
        if case == "missing-read"
        else "no rows"
        if case == "foreign-read"
        else "outside frozen demand"
        if case == "operation"
        else "source filter requires JSON string or explicit null"
    )
    with pytest.raises(DBAPIError, match=expected), connection.begin_nested():
        connection.execute(query, values)


@pytest.mark.parametrize("runtime", ["absent", "exact", "missing"])
def test_program_execution_inspection_returns_only_exact_selected_contract_runtime(
    native_rollback, runtime
):
    from corpus_structure.semantic.data_operation_read_native import _inspection_programs
    from semantic.test_data_operation_compiler_native import RELEASE, _admit, _archive, _install

    connection = native_rollback.connection
    _install(connection)
    payload, _ = _archive(connection)
    _admit(connection, payload)
    for program in _inspection_programs(metadata):
        execute_native_sql(connection, program)
    manifest, archive = b'{"retained":"manifest"}', b"actual retained runtime archive"
    connection.execute(
        insert(metadata.tables["sem.runtime_binding"]).values(
            release_id=RELEASE,
            runtime_id="runtime:exact",
            manifest_bytes=manifest,
            archive_bytes=archive,
            execution_profile="execution:literal",
        )
    )
    request = dict(release_id=RELEASE, operation_id="compiler:literal")
    if runtime != "absent":
        request["runtime_id"] = "runtime:" + runtime

    def inspect():
        return connection.scalar(
            text("SELECT ops.inspect_data_execution(CAST(:request AS jsonb))"),
            {"request": canonical_bytes(request).decode()},
        )

    if runtime == "missing":
        with pytest.raises(DBAPIError, match="no rows"), connection.begin_nested():
            inspect()
    else:
        assert inspect() == dict(
            payload=dict(
                recipe="recipe:literal",
                profile="deterministic",
                implementation_revision="literal-implementation",
                input_roles=[],
                output_roles=payload["operations"][0]["output_roles"],
                runtime=None
                if runtime == "absent"
                else dict(
                    manifest_sha256=sha256(manifest).hexdigest(),
                    archive_sha256=sha256(archive).hexdigest(),
                ),
            )
        )
