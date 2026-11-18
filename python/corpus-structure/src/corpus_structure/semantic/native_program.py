"""Lower model-owned PostgreSQL programs to the existing native authoring boundary.

Core and pglast supply statements and expressions. Only procedural framing is
rendered here. This module does not bind a catalog or authorize execution.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal, assert_never

from pglast import ast, enums
from pglast.stream import RawStream, maybe_double_quote_name
from sqlalchemy import Column, Table, cast, literal_column, null, select
from sqlalchemy.dialects.postgresql import dialect
from sqlalchemy.sql import visitors
from sqlalchemy.sql.dml import Insert
from sqlalchemy.sql.elements import BindParameter, ClauseElement, ColumnClause, TextClause
from sqlalchemy.types import TypeEngine

from .native_call_contracts import NATIVE_FIELD_TYPES, OperationCallBinding
from .prepared_sql import prepare_sql

type Expression = ast.Node | ClauseElement


def _names(*identifiers: str) -> tuple[ast.String, ...]:
    for name in identifiers:
        _identifier(name)
    return tuple(ast.String(sval=name) for name in identifiers)


def _identifier(name: str) -> str:
    if not name or "\0" in name or len(name.encode()) > 63:
        raise ValueError("invalid PostgreSQL identifier")
    return maybe_double_quote_name(name)


def pg_type(*identifiers: str) -> ast.TypeName:
    if not identifiers:
        raise ValueError("PostgreSQL type requires its name")
    if len(identifiers) == 1 and identifiers[0] in {
        "bool",
        "float4",
        "float8",
        "int2",
        "int4",
        "int8",
    }:
        # Match the parser's built-in type nodes so routine declarations and ACLs
        # use the same identity spelling (for example, bigint instead of int8).
        identifiers = ("pg_catalog", *identifiers)
    return ast.TypeName(names=_names(*identifiers), typemod=-1)


def variable(name: str, field: str | None = None) -> ast.ColumnRef:
    return ast.ColumnRef(fields=_names(name) if field is None else _names(name, field))


def core_variable(name: str, type_: TypeEngine[Any], field: str | None = None) -> ColumnClause[Any]:
    """A lexical PL/pgSQL reference with a declared PostgreSQL/driver type."""
    return literal_column(RawStream()(variable(name, field)), type_=type_)


def core_relation_row(relation: Table) -> ColumnClause[Any]:
    """Select a composite in the server's row-type order."""
    names = (relation.name,) if relation.schema is None else (relation.schema, relation.name)
    return literal_column(RawStream()(ast.ColumnRef(fields=(*_names(*names), ast.A_Star()))))


def core_parameter(position: int, type_: TypeEngine[Any]) -> ColumnClause[Any]:
    if position < 1:
        raise ValueError("native parameter numbering starts at one")
    return literal_column(RawStream()(ast.ParamRef(number=position)), type_=type_)


def call(schema: str, name: str, *arguments: ast.Node) -> ast.FuncCall:
    return ast.FuncCall(funcname=_names(schema, name), args=arguments or None)


def literal(value: str | int | bool | None) -> ast.A_Const:
    if value is None:
        return ast.A_Const(isnull=True)
    if isinstance(value, bool):
        node = ast.Boolean(boolval=value)
    elif isinstance(value, int):
        node = ast.Integer(ival=value) if -(2**31) <= value < 2**31 else ast.Float(fval=str(value))
    else:
        node = ast.String(sval=value)
    return ast.A_Const(isnull=False, val=node)


def _render(expression: Expression) -> str:
    if isinstance(expression, ast.Node):
        return RawStream()(expression)
    for child in visitors.iterate(expression):
        if isinstance(child, TextClause):
            raise ValueError("native programs require structured Core or PostgreSQL nodes")
        if isinstance(child, BindParameter) and (child.required or child.callable is not None):
            raise ValueError(f"native definition has an unresolved SQL parameter: {child.key}")
    return str(
        expression.compile(
            dialect=dialect(paramstyle="named"), compile_kwargs={"literal_binds": True}
        )
    )


def column_type(column: Column[Any]) -> ast.TypeName:
    """Retain a model-selected PostgreSQL cast as a native declaration type."""
    projection = (
        prepare_sql(_render(select(cast(null(), column.type))), source="native column type")
        .statements[0]
        .stmt
    )
    if not isinstance(projection, ast.SelectStmt) or not projection.targetList:
        raise ValueError("native output type requires one typed projection")
    value = projection.targetList[0].val
    if not isinstance(value, ast.TypeCast) or value.typeName is None:
        raise ValueError("native output type requires a model-selected cast")
    return value.typeName


def _statement(expression: Expression) -> str:
    sql = _render(expression)
    if len(prepare_sql(sql, source="native program statement").statements) != 1:
        raise ValueError("native program step requires one PostgreSQL statement")
    return sql


@dataclass(frozen=True)
class Parameter:
    name: str
    type_: ast.TypeName
    default: ast.Node | None = None


@dataclass(frozen=True)
class Local:
    name: str
    type_: ast.TypeName | Table
    initial: Expression | None = None


@dataclass(frozen=True)
class Sql:
    statement: Expression


@dataclass(frozen=True)
class Assign:
    target: str
    value: Expression


@dataclass(frozen=True)
class Perform:
    value: Expression


@dataclass(frozen=True)
class PerformQuery:
    """Execute one structured SELECT for its effects without retaining rows."""

    query: Expression


@dataclass(frozen=True)
class SelectInto:
    query: Expression
    targets: tuple[str, ...]
    strict: bool = False


@dataclass(frozen=True)
class Raise:
    message: str | Expression
    sqlstate: str


@dataclass(frozen=True)
class If:
    condition: Expression
    then: tuple[Statement, ...]
    otherwise: tuple[Statement, ...] = ()


@dataclass(frozen=True)
class While:
    condition: Expression
    body: tuple[Statement, ...]


@dataclass(frozen=True)
class ForQuery:
    targets: tuple[str, ...]
    query: Expression
    body: tuple[Statement, ...]


@dataclass(frozen=True)
class ForRelation:
    """Scan a checked regclass with model-owned named columns and ordering."""

    targets: tuple[str, ...]
    columns: tuple[str, ...]
    relation: ast.Node
    order_by: tuple[Expression, ...]
    body: tuple[Statement, ...]


@dataclass(frozen=True)
class ReturnQuery:
    query: Expression


@dataclass(frozen=True)
class Return:
    value: Expression | None = None


@dataclass(frozen=True)
class Continue:
    """Continue the enclosing native query loop."""


@dataclass(frozen=True)
class CatchCheckViolation:
    """An item subtransaction catches only PostgreSQL check_violation (23514)."""

    body: tuple[Statement, ...]
    handler: tuple[Statement, ...]


type Statement = (
    Sql
    | Continue
    | CatchCheckViolation
    | Assign
    | Perform
    | PerformQuery
    | SelectInto
    | Raise
    | If
    | While
    | ForQuery
    | ForRelation
    | ReturnQuery
    | Return
)


@dataclass(frozen=True)
class Block:
    statements: tuple[Statement, ...]
    locals: tuple[Local, ...] = ()


def _targets(targets: tuple[str, ...]) -> str:
    if not targets or len(set(targets)) != len(targets):
        raise ValueError("procedural projection requires distinct declared targets")
    return ", ".join(map(_identifier, targets))


def _statements(statements: tuple[Statement, ...], indent: str) -> str:
    return (
        "\n".join(indent + _step(statement, indent + " ") + ";" for statement in statements)
        or indent + "NULL;"
    )


def _step(statement: Statement, nested: str) -> str:
    match statement:
        case Sql(sql):
            # Native effects have no client to receive an implicitly returned identity.
            return _statement(sql.inline() if isinstance(sql, Insert) else sql)
        case Assign(target, value):
            return f"{_identifier(target)} := {_render(value)}"
        case Perform(value):
            return "PERFORM " + _render(value)
        case PerformQuery(query):
            sql = _statement(query)
            root = prepare_sql(sql, source="native perform query").statements[0].stmt
            if (
                not isinstance(root, ast.SelectStmt)
                or root.withClause is not None
                or root.op not in (None, enums.SetOperation.SETOP_NONE)
                or not sql.startswith("SELECT ")
            ):
                raise ValueError("native PERFORM query requires one ordinary structured SELECT")
            return "PERFORM" + sql[6:]
        case SelectInto(query, targets, strict):
            # PL/pgSQL allows INTO after the query clauses. This leaves Core
            # in charge of projection, correlation, and precedence.
            return _statement(query) + " INTO " + ("STRICT " if strict else "") + _targets(targets)
        case Raise(message, state):
            if (
                len(state) != 5
                or not state.isascii()
                or not state.isalnum()
                or state != state.upper()
            ):
                raise ValueError("procedural refusal requires an explicit SQLSTATE")
            expression = literal(message) if isinstance(message, str) else message
            return f"RAISE EXCEPTION USING MESSAGE = {_render(expression)}, ERRCODE = '{state}'"
        case If(condition, then, otherwise):
            body = _statements(then, nested)
            if otherwise:
                body += f"\n{nested[:-1]}ELSE\n" + _statements(otherwise, nested)
            return f"IF {_render(condition)} THEN\n{body}\n{nested[:-1]}END IF"
        case While(condition, body):
            return f"WHILE {_render(condition)} LOOP\n{_statements(body, nested)}\n{nested[:-1]}END LOOP"
        case ForQuery(targets, query, body):
            return (
                f"FOR {_targets(targets)} IN {_statement(query)} LOOP\n"
                f"{_statements(body, nested)}\n{nested[:-1]}END LOOP"
            )
        case ForRelation(targets, columns, relation, order_by, body):
            if not columns or not order_by:
                raise ValueError("dynamic relation scan requires its columns and ordering")
            query = (
                "SELECT "
                + ", ".join(_identifier(name).replace("%", "%%") for name in columns)
                + " FROM %s ORDER BY "
            )
            query += ", ".join(_render(value).replace("%", "%%") for value in order_by)
            dynamic = call("pg_catalog", "format", literal(query), relation)
            return (
                f"FOR {_targets(targets)} IN EXECUTE {_render(dynamic)} LOOP\n"
                f"{_statements(body, nested)}\n{nested[:-1]}END LOOP"
            )
        case ReturnQuery(query):
            return "RETURN QUERY " + _statement(query)
        case Continue():
            return "CONTINUE"
        case CatchCheckViolation(body, handler):
            return (
                f"BEGIN\n{_statements(body, nested)}\n"
                f"{nested[:-1]}EXCEPTION WHEN check_violation THEN\n"
                f"{_statements(handler, nested)}\n{nested[:-1]}END"
            )
        case Return(value):
            return "RETURN" if value is None else "RETURN " + _render(value)
    assert_never(statement)


def _body(block: Block) -> str:
    declarations = []
    for local in block.locals:
        kind = local.type_
        datatype = (
            ".".join(map(_identifier, (str(kind.schema), kind.name))) + "%ROWTYPE"
            if isinstance(kind, Table)
            else _render(kind)
        )
        spelling = f" {_identifier(local.name)} {datatype}"
        if local.initial is not None:
            spelling += " := " + _render(local.initial)
        declarations.append(spelling + ";")
    prefix = "DECLARE\n" + "\n".join(declarations) + "\n" if declarations else ""
    return prefix + "BEGIN\n" + _statements(block.statements, " ") + "\nEND"


def Do(block: Block) -> str:
    return _statement(
        ast.DoStmt(args=(ast.DefElem(defname="as", arg=ast.String(sval=_body(block))),))
    )


def function(
    schema: str,
    name: str,
    *,
    parameters: tuple[Parameter, ...],
    returns: ast.TypeName,
    body: Block,
    security_definer: bool = False,
    search_path: tuple[str, ...] = (),
    volatility: Literal["stable", "immutable", "volatile"] | None = None,
    strict: bool = False,
) -> str:
    names = tuple(item.name for item in (*parameters, *body.locals))
    if len(set(names)) != len(names):
        raise ValueError("native function requires distinct parameters and locals")
    return _routine(
        schema,
        name,
        parameters,
        returns,
        "plpgsql",
        _body(body),
        security_definer=security_definer,
        search_path=search_path,
        volatility=volatility,
        strict=strict,
    )


def sql_function(
    schema: str,
    name: str,
    *,
    parameters: tuple[Parameter, ...],
    returns: ast.TypeName,
    body: Expression,
    security_definer: bool = False,
    search_path: tuple[str, ...] = (),
    volatility: Literal["stable", "immutable", "volatile"] | None = None,
    strict: bool = False,
) -> str:
    """Generate a SQL-language function under its existing text-body profile."""
    return _routine(
        schema,
        name,
        parameters,
        returns,
        "sql",
        _statement(body),
        security_definer=security_definer,
        search_path=search_path,
        volatility=volatility,
        strict=strict,
    )


def _routine(
    schema: str,
    name: str,
    parameters: tuple[Parameter, ...],
    returns: ast.TypeName,
    language: Literal["sql", "plpgsql"],
    body: str,
    *,
    security_definer: bool,
    search_path: tuple[str, ...],
    volatility: Literal["stable", "immutable", "volatile"] | None,
    strict: bool,
) -> str:
    if security_definer and not search_path:
        raise ValueError("security definer function requires its declared search path")
    names = tuple(item.name for item in parameters)
    if len(set(names)) != len(names):
        raise ValueError("native function requires distinct parameters")
    if names:
        _names(*names)
    options = [ast.DefElem(defname="language", arg=ast.String(sval=language))]
    if volatility is not None:
        options.append(ast.DefElem(defname="volatility", arg=ast.String(sval=volatility)))
    if strict:
        options.append(ast.DefElem(defname="strict", arg=ast.Boolean(boolval=True)))
    if security_definer:
        options.append(ast.DefElem(defname="security", arg=ast.Boolean(boolval=True)))
    if search_path:
        options.append(
            ast.DefElem(
                defname="set",
                arg=ast.VariableSetStmt(
                    kind=enums.VariableSetKind.VAR_SET_VALUE,
                    name="search_path",
                    args=tuple(literal(item) for item in search_path),
                ),
            )
        )
    options.append(ast.DefElem(defname="as", arg=(ast.String(sval=body),)))
    return _statement(
        ast.CreateFunctionStmt(
            replace=True,
            funcname=_names(schema, name),
            parameters=tuple(
                ast.FunctionParameter(
                    name=parameter.name,
                    argType=parameter.type_,
                    defexpr=parameter.default,
                    mode=enums.FunctionParameterMode.FUNC_PARAM_DEFAULT,
                )
                for parameter in parameters
            )
            or None,
            returnType=returns,
            options=tuple(options),
        )
    )


def void_call_function(
    binding: OperationCallBinding,
    *,
    body: Block,
    security_definer: bool = False,
    search_path: tuple[str, ...] = (),
) -> str:
    """Generate a protected effect's declaration from the resolved caller contract."""
    if (
        binding.backend != "native"
        or binding.result_mode != "void"
        or binding.result_fields
        or binding.cardinality != "none"
    ):
        raise ValueError(f"{binding.id}: expected a native void effect")
    names = binding.symbol.split(".")
    if len(names) != 2:
        raise ValueError(f"{binding.id}: expected an explicitly qualified native symbol")
    parameters = []
    for field in binding.parameters:
        resolved = field.resolved
        if (
            resolved is None
            or field.native_parameter is None
            or resolved.kind not in NATIVE_FIELD_TYPES
        ):
            raise ValueError(f"{binding.id}.{field.name}: unresolved native parameter")
        native = pg_type(
            "int4" if field.native_type == "integer" else NATIVE_FIELD_TYPES[resolved.kind][0]
        )
        if resolved.multivalued:
            native.arrayBounds = (ast.Integer(ival=-1),)
        parameters.append(Parameter(field.native_parameter, native))
    return function(
        names[0],
        names[1],
        parameters=tuple(parameters),
        returns=pg_type("void"),
        body=body,
        security_definer=security_definer,
        search_path=search_path,
    )
