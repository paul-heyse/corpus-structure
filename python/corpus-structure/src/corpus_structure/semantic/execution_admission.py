"""Trusted execution compatibility at the immutable release activation boundary.

Contract compilation establishes the model's meaning and implementation requirements.
It does not establish that those requirements have native enforcement. In particular,
the execution lifecycle contracts cannot activate until their SP-C03 guards exist.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from .refusals import SemanticRefusal
from .types import PreparedRelease

if TYPE_CHECKING:
    from sqlalchemy import Connection

# Code support is distinct from deployment: composed admission additionally checks
# the exact native implementation on the caller's connection. This set is code-owned.
_NATIVE_CAPABILITIES = frozenset(
    {
        "semantic_registry",
        "scoped_publication",
        "typed_values",
        "execution.lifecycle.v1",
        "execution.identity_exclusions.v1",
        "execution.reference_evaluation.v1",
        "execution.selected_result.v1",
        "conditional_rules_native",
    }
)


class ExecutionAdmissionError(SemanticRefusal):
    """The archived binding lacks a compatible trusted enforcing implementation."""


def admit_execution_release(
    prepared: PreparedRelease, *, connection: Connection | None = None
) -> None:
    """Check current code compatibility and refuse unavailable required semantics.

    Pure compiled products may be reused by the compiler. Database state and permissions
    are checked by their existing owners on every activation and are never cached here.
    """
    if prepared.execution_model_id is not None:
        from .contracts import bound_execution_model

        current = bound_execution_model(prepared)
        for operation in current.operations:
            if operation.implementation is not None:
                current.require_operation(operation.id)
        missing_requirements = set(current.required_capabilities) - set(
            prepared.required_capabilities
        )
        if missing_requirements:
            raise ExecutionAdmissionError(
                "release omits required execution capabilities: "
                + ", ".join(sorted(missing_requirements))
            )
    if prepared.execution_model_id is None and set(prepared.required_capabilities) & {
        "execution.lifecycle.v1",
        "execution.identity_exclusions.v1",
        "conditional_rules_native",
    }:
        raise ExecutionAdmissionError("native execution capabilities require a composed model")
    unavailable = set(prepared.required_capabilities) - _NATIVE_CAPABILITIES
    if unavailable:
        raise ExecutionAdmissionError(
            "required native enforcement is unavailable: " + ", ".join(sorted(unavailable))
        )

    if prepared.execution_model_id is not None:
        if connection is None:
            raise ExecutionAdmissionError("composed admission requires verified native deployment")
        require_native_execution(connection, prepared)


def _verify_deployment_functions(connection: Connection) -> None:
    from sqlalchemy import text

    for signature, digest, security, language in (
        ("data.execution_contract_descriptor()", _DESCRIPTOR_SHA256, False, "sql"),
        ("data.require_execution_release(text)", _REQUIRE_SHA256, True, "plpgsql"),
    ):
        available = (
            connection.execute(
                text("""
          SELECT encode(sha256(convert_to(p.prosrc,'UTF8')),'hex')=:digest
             AND p.prosecdef=:security AND l.lanname=:language
             AND p.proconfig=ARRAY['search_path=pg_catalog, pg_temp']
             AND pg_get_userbyid(p.proowner)='corpus_sem_publisher'
             AND NOT EXISTS(SELECT FROM aclexplode(COALESCE(p.proacl,acldefault('f',p.proowner))) a
                            WHERE a.grantee=0 AND a.privilege_type='EXECUTE') AS compatible,
             encode(sha256(convert_to(p.prosrc,'UTF8')),'hex') AS actual_hash,
             p.proconfig AS configuration, pg_get_userbyid(p.proowner) AS owner,
             p.prosecdef AS security, l.lanname AS language,
             EXISTS(SELECT FROM aclexplode(COALESCE(p.proacl,acldefault('f',p.proowner))) a
                    WHERE a.grantee=0 AND a.privilege_type='EXECUTE') AS public_execute,
             :digest AS expected_hash
          FROM pg_proc p JOIN pg_language l ON l.oid=p.prolang
          WHERE p.oid=to_regprocedure(:signature)
        """),
                dict(signature=signature, digest=digest, security=security, language=language),
            )
            .mappings()
            .one_or_none()
        )
        if available is None or available["compatible"] is not True:
            raise ExecutionAdmissionError(
                "native execution deployment differs: "
                + signature
                + " "
                + repr(dict(available) if available is not None else None)
            )

    from pglast import parse_sql
    from pglast.stream import RawStream
    from sqlalchemy.dialects.postgresql import dialect

    from .native_products import selected_fact_query

    actual_view = connection.execute(
        text("SELECT pg_get_viewdef('data.selected_fact'::regclass,true)")
    ).scalar_one()
    expected_view = str(selected_fact_query().compile(dialect=dialect()))
    actual_statement = parse_sql(actual_view)[0].stmt
    expected_statement = parse_sql(expected_view)[0].stmt
    if actual_statement is None or expected_statement is None:
        raise ExecutionAdmissionError("native selected-fact view has no statement")
    if RawStream()(actual_statement) != RawStream()(expected_statement):
        raise ExecutionAdmissionError("native selected-fact view differs from its model projection")


def require_native_execution(connection: Connection, prepared: PreparedRelease) -> None:
    from sqlalchemy import text
    from sqlalchemy.exc import DBAPIError

    _verify_deployment_functions(connection)
    try:
        connection.execute(
            text("SELECT data.require_execution_release(:release)"),
            {"release": prepared.release_id},
        )
    except DBAPIError as exc:
        if getattr(exc.orig, "sqlstate", None) not in {"23514", "P0001"}:
            raise
        reason = str(exc.orig).splitlines()[0]
        raise ExecutionAdmissionError(
            "native execution deployment or archived binding is incompatible: "
            + reason
            + "; inspect the owning contract and derive a new reviewed revision with "
            "ci schema derive --out <new-directory>"
        ) from exc


def require_archive_fence(connection: Connection) -> None:
    """Archive under either the exact refusal fence or the enforcing deployment."""
    from sqlalchemy import text

    row = (
        connection.execute(
            text("""
      SELECT encode(sha256(convert_to(p.prosrc,'UTF8')),'hex') AS digest,
             pg_get_userbyid(p.proowner) AS owner,
             p.prosecdef,p.proconfig,
             ARRAY(SELECT a.attname::text FROM unnest(t.tgattr::smallint[])
                   WITH ORDINALITY attrs(num,position)
                   JOIN pg_attribute a ON a.attrelid=t.tgrelid AND a.attnum=attrs.num
                   ORDER BY attrs.position) AS update_columns,
             (SELECT pg_get_userbyid(nspowner) FROM pg_namespace
              WHERE nspname='sem') AS schema_owner
      FROM pg_trigger t JOIN pg_proc p ON p.oid=t.tgfoid
      WHERE t.tgrelid='data.realization'::regclass AND t.tgname='guard_execution_admission'
        AND NOT t.tgisinternal AND t.tgenabled IN ('O','A') AND t.tgqual IS NULL AND t.tgnargs=0
        AND t.tgtype=23 AND p.oid=to_regprocedure('data.guard_execution_admission()')
    """)
        )
        .mappings()
        .one_or_none()
    )
    if row is None or row["proconfig"] != ["search_path=pg_catalog, pg_temp"]:
        raise ExecutionAdmissionError("native execution archive fence is not deployed")
    if (
        row["digest"] == _REFUSAL_SHA256
        and row["prosecdef"] is False
        and row["owner"] == row["schema_owner"]
        and row["update_columns"] == ["release_id"]
    ):
        return
    if (
        row["digest"] == _GUARD_SHA256
        and row["owner"] == "corpus_sem_publisher"
        and row["prosecdef"] is True
        and row["update_columns"] == []
    ):
        _verify_deployment_functions(connection)
        return
    raise ExecutionAdmissionError("native execution archive fence differs from trusted enforcement")


# Frozen from reviewed migration ASTs through semantic_0058.
# Schema derive emits the corresponding SQL.
_DESCRIPTOR_SHA256 = "12cfef1326ef85ed6f4d25cc21fec846b1ebda6df63c2b79bc0b97f323900c85"
_REQUIRE_SHA256 = "a78b1df7fae951c92c2d7387ead804e9471e2e257f28e157cfbad09ba5869310"
_REFUSAL_SHA256 = "e5dc0f2a81371d4091c1d80a4fe4de6f5c94f519b9d916ffae486e9b75f4e462"
_GUARD_SHA256 = "225ab497a6a3c33dfa895ba3ca977de9a27f86d7777c84f92e0bc47edbba98a6"
