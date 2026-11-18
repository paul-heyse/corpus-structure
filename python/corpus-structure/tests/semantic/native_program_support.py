"""Install one current generated routine under an isolated test-local name."""

from pglast import ast, parse_sql
from pglast.stream import RawStream


def routine_declaration(source: str, schema: str, name: str, *, temporary: bool = True) -> str:
    (owned,) = (
        entry.stmt
        for entry in parse_sql(source)
        if isinstance(entry.stmt, ast.CreateFunctionStmt)
        and tuple(part.sval for part in entry.stmt.funcname or ()) == (schema, name)
    )
    if not temporary:
        return RawStream()(owned)
    owned.funcname = (ast.String(sval="pg_temp"), ast.String(sval=name))
    rendered = RawStream()(owned)
    # A recursive isolated routine calls its own test-local declaration.
    return rendered.replace(f"{schema}.{name}(", f"pg_temp.{name}(")
