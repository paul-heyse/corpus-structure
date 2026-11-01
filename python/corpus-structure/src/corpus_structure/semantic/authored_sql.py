"""Bounded authored SELECT admission; ordinary Core queries do not pass through here.

The parser establishes syntax/dependencies. PostgreSQL establishes column/type/access binding
under a real restricted login, with a catalog-only search path and a read-only transaction.
Only explicitly supported built-in types/functions/operators reach PostgreSQL analysis.
"""

from __future__ import annotations

import json
from collections.abc import Mapping
from dataclasses import dataclass
from hashlib import sha256
from importlib.metadata import version
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from .types import PreparedRelease

from pglast import ast
from pglast.stream import RawStream
from pglast.visitors import Visitor, referenced_relations
from sqlalchemy import Connection, MetaData, select, text

from .identity import canonical_bytes
from .prepared_sql import PreparedSQL, SQLSyntaxError, prepare_sql

COMPILER_VERSION = "authored-select-1"
SAFE_FUNCTIONS = frozenset({"count", "min", "max", "sum", "avg", "abs", "length", "lower", "upper"})
SAFE_TYPES = frozenset(
    {
        "text",
        "varchar",
        "bpchar",
        "bool",
        "int2",
        "int4",
        "int8",
        "numeric",
        "float4",
        "float8",
        "bytea",
        "jsonb",
        "date",
        "timestamp",
        "timestamptz",
        "uuid",
    }
)
SAFE_OPERATORS = frozenset(
    {"=", "<>", "!=", "<", ">", "<=", ">=", "+", "-", "*", "/", "%", "~~", "!~~", "~~*", "!~~*"}
)
SAFE_NODES = frozenset(
    {
        "RawStmt",
        "SelectStmt",
        "ResTarget",
        "ColumnRef",
        "A_Star",
        "String",
        "Integer",
        "Float",
        "Boolean",
        "A_Const",
        "RangeVar",
        "Alias",
        "JoinExpr",
        "A_Expr",
        "BoolExpr",
        "NullTest",
        "BooleanTest",
        "SortBy",
        "WithClause",
        "CommonTableExpr",
        "RangeSubselect",
        "SubLink",
        "FuncCall",
        "TypeCast",
        "TypeName",
        "CoalesceExpr",
        "CaseExpr",
        "CaseWhen",
    }
)


class SQLAdmissionError(ValueError):
    def __init__(self, message: str, location: int | None = None):
        self.location = location
        self.message = message
        super().__init__(
            f"{message}" + (f" at character {location}" if location is not None else "")
        )


@dataclass(frozen=True)
class AuthoredSQL:
    sql: str
    release_id: str
    physical_id: str
    relations: tuple[str, ...]
    functions: tuple[str, ...]
    catalog_dependencies: tuple[tuple[str, ...], ...]
    parser_version: str
    server_version: str
    compiler_version: str = COMPILER_VERSION

    @property
    def content(self) -> bytes:
        from dataclasses import asdict

        return canonical_bytes(asdict(self))

    @property
    def digest(self) -> str:
        return sha256(self.content).hexdigest()


class _Inspect(Visitor):
    def __init__(self) -> None:
        super().__init__()
        self.functions: set[str] = set()
        self.visit = self.inspect_node

    def inspect_node(self, ancestors: Any, node: Any) -> None:
        kind = type(node).__name__
        if kind not in SAFE_NODES:
            raise SQLAdmissionError(
                f"unsupported authored SQL node {kind}", getattr(node, "location", None)
            )
        if isinstance(node, ast.SelectStmt) and (node.intoClause or node.lockingClause):
            raise SQLAdmissionError("SELECT INTO and row locking are unsupported")
        if isinstance(node, ast.FuncCall):
            name = tuple(n.sval for n in node.funcname or ())
            if len(name) != 2 or name[0] != "pg_catalog" or name[1] not in SAFE_FUNCTIONS:
                raise SQLAdmissionError(f"unapproved function {'.'.join(name)}", node.location)
            self.functions.add(name[1])
        if isinstance(node, ast.TypeName):
            name = tuple(n.sval for n in node.names or ())
            if len(name) == 1:
                name = ("pg_catalog", *name)
            if len(name) != 2 or name[0] != "pg_catalog" or name[1] not in SAFE_TYPES:
                raise SQLAdmissionError(f"unsupported type {'.'.join(name)}", node.location)
            if node.arrayBounds or node.setof or node.pct_type:
                raise SQLAdmissionError(
                    "array/set/column type casts are unsupported", node.location
                )
        if isinstance(node, ast.A_Expr):
            name = tuple(n.sval for n in node.name or ())
            if name and (
                name[-1] not in SAFE_OPERATORS or (len(name) > 1 and name[:-1] != ("pg_catalog",))
            ):
                raise SQLAdmissionError(f"unsupported operator {'.'.join(name)}", node.location)


def _syntax(sql: str | PreparedSQL, metadata: MetaData) -> tuple[tuple[str, ...], tuple[str, ...]]:
    try:
        prepared = prepare_sql(sql)
    except SQLSyntaxError as exc:
        raise SQLAdmissionError(str(exc), exc.position) from exc
    tree = prepared.statements
    if len(tree) != 1 or not isinstance(tree[0].stmt, ast.SelectStmt):
        raise SQLAdmissionError("exactly one SELECT is required")
    inspection = _Inspect()
    try:
        inspection(tree)
    except SQLAdmissionError as exc:
        # pglast's high-level AST constructor already adapts native offsets to Unicode.
        raise SQLAdmissionError(f"{prepared.source}: {exc.message}", exc.location) from exc
    # pglast handles CTE lexical scopes, including nested shadowing, rather than a regex scanner.
    references = referenced_relations(tree)
    known = {
        RawStream()(ast.RangeVar(schemaname=t.schema, relname=t.name, inh=True)): name
        for name, t in metadata.tables.items()
    }
    unknown = references - known.keys()
    if unknown:
        raise SQLAdmissionError(f"unknown or unqualified relations: {', '.join(sorted(unknown))}")
    return tuple(sorted(known[r] for r in references)), tuple(sorted(inspection.functions))


def admit_sql(
    conn: Connection,
    sql: str,
    *,
    release_id: str,
    metadata: MetaData,
    physical_id: str,
    execution_role: str = "corpus_sem_reader",
) -> AuthoredSQL:
    """Analyze supported SQL without execution. Caller supplies a fresh restricted connection.

    The resulting artifact belongs in the exact release archive. Its dependencies must be
    re-admitted after a physical/catalog/compiler change; a parser fingerprint is never its ID.
    """
    relations, functions = _syntax(sql, metadata)
    if conn.in_transaction():
        raise SQLAdmissionError("admission needs a fresh connection")
    dependencies: list[tuple[str, ...]] = []
    with conn.begin():
        conn.exec_driver_sql("SET TRANSACTION READ ONLY")
        conn.exec_driver_sql("SET LOCAL search_path = pg_catalog")
        role = conn.execute(
            text(
                "SELECT current_user, session_user, rolsuper, rolcreaterole, "
                "rolcreatedb, rolbypassrls "
                "FROM pg_roles WHERE rolname=current_user"
            )
        ).one()
        member = conn.scalar(
            text("SELECT pg_has_role(current_user,:required,'USAGE')"), {"required": execution_role}
        )
        if role[0] != role[1] or not member or any(role[2:]):
            raise SQLAdmissionError(
                "catalog admission requires the actual restricted execution login"
            )
        from sqlalchemy.exc import DBAPIError

        try:
            conn.execute(text("SELECT data.require_runtime_principal('read')"))
        except DBAPIError as exc:
            raise SQLAdmissionError(
                "catalog admission requires restricted read capabilities"
            ) from exc
        for name in relations:
            t = metadata.tables[name]
            columns = conn.execute(
                text(
                    "SELECT c.oid, c.relkind, a.attname, n.nspname, y.typname, "
                    "pg_has_role(current_user,c.relowner,'USAGE'), "
                    "has_schema_privilege(current_user,c.relnamespace,'CREATE') "
                    "FROM pg_class c JOIN pg_namespace s ON s.oid=c.relnamespace "
                    "JOIN pg_attribute a ON a.attrelid=c.oid AND a.attnum>0 AND NOT a.attisdropped "
                    "JOIN pg_type y ON y.oid=a.atttypid "
                    "JOIN pg_namespace n ON n.oid=y.typnamespace "
                    "WHERE s.nspname=:schema AND c.relname=:name ORDER BY a.attnum"
                ),
                {"schema": t.schema, "name": t.name},
            ).all()
            if not columns or any(
                r[1] not in ("r", "p")
                or r[3] != "pg_catalog"
                or r[4] not in SAFE_TYPES
                or r[5]
                or r[6]
                for r in columns
            ):
                raise SQLAdmissionError(f"unsupported or writable catalog dependency {name}")
            dependencies.extend((name, str(r[0]), r[2], r[3], r[4]) for r in columns)
        for function in functions:
            rows = conn.execute(
                text(
                    "SELECT p.oid, pg_get_function_identity_arguments(p.oid), "
                    "p.provolatile, p.prosecdef "
                    "FROM pg_proc p JOIN pg_namespace n ON n.oid=p.pronamespace "
                    "WHERE n.nspname='pg_catalog' AND p.proname=:name ORDER BY p.oid"
                ),
                {"name": function},
            ).all()
            if not rows or any(r[2] == "v" or r[3] for r in rows):
                raise SQLAdmissionError(f"unsupported catalog function pg_catalog.{function}")
            dependencies.extend(("function", function, str(r[0]), r[1], r[2]) for r in rows)
        # EXPLAIN without ANALYZE invokes PostgreSQL name/type/access analysis. Unknown functions
        # and custom types were refused above, before any planner constant folding can call them.
        # exec_driver_sql preserves exact authored text, including colons and percent literals.
        driver = conn.connection.driver_connection
        if driver is None:
            raise SQLAdmissionError("PostgreSQL driver is unavailable")
        with driver.cursor() as cur:
            cur.execute("EXPLAIN (FORMAT JSON) " + sql, prepare=False)
            cur.fetchone()
        server_version = conn.exec_driver_sql("SHOW server_version").scalar_one()
    return AuthoredSQL(
        sql,
        release_id,
        physical_id,
        relations,
        functions,
        tuple(dependencies),
        version("pglast"),
        server_version,
    )


def decode_artifact(content: bytes) -> dict[str, Any]:
    """Read archived data for diagnostics; admission is never inferred from this decode."""
    return json.loads(content)


def has_authored_sql(prepared: PreparedRelease) -> bool:
    """The immutable dependency manifest declares whether reader analysis is required."""
    return any(
        name.startswith("authored-sql/")
        for name, _ in json.loads(prepared.manifest)["dependencies"]
    )


def analyze_archived_sql(conn: Connection, release_id: str) -> dict[str, AuthoredSQL]:
    """Analyze archived inputs under the actual reader; return products without writing."""
    from .metadata import PHYSICAL_MODEL_ID, metadata, table

    inputs = table("sem.input")
    if conn.in_transaction():
        raise SQLAdmissionError("archive analysis requires a fresh reader connection")
    with conn.begin():
        conn.exec_driver_sql("SET TRANSACTION READ ONLY")
        rows = conn.execute(
            select(inputs.c.input_name, inputs.c.content)
            .where(
                inputs.c.release_id == release_id,
                inputs.c.input_kind == "dependency",
                inputs.c.input_name.startswith("authored-sql/"),
            )
            .order_by(inputs.c.input_name)
        ).all()
    products = {}
    for name, content in rows:
        if not name.endswith(".sql") or len(name) <= len("authored-sql/.sql"):
            raise SQLAdmissionError(f"invalid reserved authored SQL dependency name {name}")
        products[name] = admit_sql(
            conn,
            bytes(content).decode("utf-8"),
            release_id=release_id,
            metadata=metadata,
            physical_id=PHYSICAL_MODEL_ID,
        )
    return products


def admit_archived_sql(
    conn: Connection,
    release_id: str,
    *,
    reader_conn: Connection | None = None,
    analyzed: Mapping[str, AuthoredSQL] | None = None,
) -> tuple[AuthoredSQL, ...]:
    """Admit reserved exact SQL dependencies before activation, on its caller transaction.

    Raw SQL belongs to the release digest; native catalog admission is a derived deployment
    artifact. Keeping those separate avoids an impossible self-referential release identity.
    """
    from .metadata import PHYSICAL_MODEL_ID, metadata, table

    inputs = table("sem.input")
    admitted = table("sem.sql_admission")
    rows = conn.execute(
        select(inputs.c.input_name, inputs.c.content)
        .where(
            inputs.c.release_id == release_id,
            inputs.c.input_kind == "dependency",
            inputs.c.input_name.startswith("authored-sql/"),
        )
        .order_by(inputs.c.input_name)
    ).all()
    if analyzed is not None and set(analyzed) != {name for name, _ in rows}:
        raise SQLAdmissionError("analyzed SQL input set differs")
    if rows and reader_conn is None and analyzed is None:
        raise SQLAdmissionError("authored SQL activation requires a restricted reader connection")
    artifacts = []
    for name, content in rows:
        if not name.endswith(".sql") or len(name) <= len("authored-sql/.sql"):
            raise SQLAdmissionError(f"invalid reserved authored SQL dependency name {name}")
        try:
            sql = bytes(content).decode("utf-8")
        except UnicodeDecodeError as exc:
            raise SQLAdmissionError(f"authored SQL {name} is not UTF-8") from exc
        if analyzed is not None:
            artifact = analyzed[name]
            if (artifact.sql, artifact.release_id, artifact.physical_id) != (
                sql,
                release_id,
                PHYSICAL_MODEL_ID,
            ):
                raise SQLAdmissionError("analyzed SQL binding differs")
        else:
            assert reader_conn is not None
            artifact = admit_sql(
                reader_conn,
                sql,
                release_id=release_id,
                metadata=metadata,
                physical_id=PHYSICAL_MODEL_ID,
            )
        values = dict(
            release_id=release_id,
            input_kind="dependency",
            input_name=name,
            physical_id=PHYSICAL_MODEL_ID,
            content=artifact.content,
            content_digest=artifact.digest,
        )
        conn.execute(
            text(
                "SELECT sem.record_sql_admission("
                ":release_id,:input_kind,:input_name,:physical_id,:content)"
            ),
            {key: value for key, value in values.items() if key != "content_digest"},
        )
        prior = conn.execute(
            select(admitted.c.content).where(
                admitted.c.release_id == release_id,
                admitted.c.input_name == name,
                admitted.c.physical_id == PHYSICAL_MODEL_ID,
            )
        ).scalar_one()
        if bytes(prior) != artifact.content:
            raise SQLAdmissionError(
                f"catalog admission changed for {name}; rebuild the realization"
            )
        artifacts.append(artifact)
    return tuple(artifacts)
