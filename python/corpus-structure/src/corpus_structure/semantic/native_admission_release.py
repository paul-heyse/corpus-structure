"""Model-bound release preconditions and exact native admission receipt programs."""

from pglast import ast, parse_sql, scan
from pglast.stream import RawStream
from sqlalchemy import Text, cast, exists, func, or_, select
from sqlalchemy.dialects.postgresql import JSONB

from .native_program import Assign, If, Perform, Raise, _statements, core_variable

CATALOG_END = " -- native catalog checks complete"


def release_preconditions(metadata):
    finalized = metadata.tables["sem.release_finalization"]
    release = metadata.tables["sem.release"]
    selected = core_variable("r", Text())
    return (
        If(~exists(select(1).select_from(finalized).where(finalized.c.release_id == selected)),
           (Raise("release is not finalized", "23514"),)),
        Perform(func.sem.require_execution_projection(selected)),
        If(~exists(select(1).select_from(release).where(release.c.release_id == selected)),
           (Raise("unknown execution release", "23514"),)),
        Assign("expected", func.data.execution_contract_descriptor()),
    )


def native_receipt_admission(metadata):
    receipt = metadata.tables["sem.deployment_admission"]
    selected = core_variable("r", Text())
    expected = core_variable("expected", JSONB())
    owner = core_variable("owner_name", Text())
    content = func.convert_to(cast(expected, Text()), "UTF8")
    identity = func.encode(func.sha256(content), "hex")
    physical_id = expected["physical_id"].astext
    recorded = exists(select(1).select_from(receipt).where(
        receipt.c.release_id == selected, receipt.c.physical_id == physical_id,
        receipt.c.deployment_id == identity, receipt.c.kind == "native", receipt.c.content == content,
    ))
    authorized = or_(
        func.pg_has_role(func.session_user(), "corpus_sem_admitter", "USAGE"),
        func.pg_has_role(func.session_user(), owner, "MEMBER"),
    )
    return (If(~recorded, (
        If(~authorized, (Raise("native admission requires restricted admission phase", "42501"),)),
        Perform(func.sem.record_deployment_admission(selected, physical_id, identity, "native", content)),
    )),)


def admission_kernel(source: str, metadata) -> str:
    """Compose typed programs at the body boundaries of the retained SQL guard."""
    statements = parse_sql(source)
    declarations = [raw.stmt for raw in statements if isinstance(raw.stmt, ast.CreateFunctionStmt)]
    if len(declarations) != 1:
        raise ValueError("admission source requires one enforcing function")
    declaration = declarations[0]
    if tuple(part.sval for part in declaration.funcname or ()) != ("data", "require_execution_release"):
        raise ValueError("admission source names another enforcing function")
    options = [option for option in declaration.options or () if option.defname == "as"]
    if len(options) != 1 or not isinstance(options[0].arg, tuple) or len(options[0].arg) != 1:
        raise ValueError("admission source requires one retained function body")
    (body_literal,) = options[0].arg
    if not isinstance(body_literal, ast.String):
        raise ValueError("admission source requires a literal retained body")
    body = body_literal.sval
    if not isinstance(body, str):
        raise ValueError("admission source requires retained body text")
    tokens = scan(body)
    openings = [token for token in tokens if token.name == "BEGIN_P"]
    endings = [token for token in tokens if token.name == "END_P"]
    if not openings or not endings:
        raise ValueError("admission source lacks its outer procedural body")
    first, last = openings[0], endings[-1]
    if last.start <= first.end or body[last.end + 1:].strip() not in {"", ";"}:
        raise ValueError("admission source has an invalid outer procedural body")
    body_literal.sval = "\n".join((
        body[:first.end + 1],
        _statements(release_preconditions(metadata), " "),
        body[first.end + 1:last.start],
        CATALOG_END,
        _statements(native_receipt_admission(metadata), " "),
        body[last.start:],
    ))
    return RawStream()(statements) + ";"
