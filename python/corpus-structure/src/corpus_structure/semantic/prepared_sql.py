"""Source-qualified process-local SQL syntax; shared nodes are read-only by contract."""

from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
from importlib.metadata import version

from pglast import ast, parse_sql
from pglast.parser import Displacements, ParseError, split


class SQLSyntaxError(ValueError):
    def __init__(self, source: str, sql: str, message: str, position: int | None):
        self.source, self.position = source, position
        self.excerpt = None
        suffix = ""
        if position is not None:
            start = sql.rfind("\n", 0, position) + 1
            end = sql.find("\n", position)
            self.excerpt = sql[start : None if end < 0 else end]
            suffix = f" at character {position}: {self.excerpt!r}"
        super().__init__(f"{source}: {message}{suffix}")


@dataclass(frozen=True)
class PreparedSQL:
    source: str
    sql: str
    statements: tuple[ast.RawStmt, ...]
    slices: tuple[slice, ...]
    parser_version: str

    @property
    def digest(self) -> str:
        return sha256(self.sql.encode()).hexdigest()

    def private_tree(self) -> tuple[ast.RawStmt, ...]:
        """A transforming consumer owns this clone; source positions still name original SQL."""
        return tuple(ast.RawStmt(item()) for item in self.statements)

    def excerpt(self, statement: int) -> str:
        return self.sql[self.slices[statement]]

    def character_position(self, byte_offset: int | None) -> int | None:
        """Only raw AST/native offsets use this conversion; ParseError is already Unicode."""
        if byte_offset is None or byte_offset < 0:
            return None
        return Displacements(self.sql)(byte_offset)


def prepare_sql(sql: str | PreparedSQL, *, source: str = "<authored SQL>") -> PreparedSQL:
    if isinstance(sql, PreparedSQL):
        return sql
    try:
        statements = parse_sql(sql)
    except ParseError as exc:
        position = exc.args[1] if len(exc.args) > 1 else None
        raise SQLSyntaxError(source, sql, str(exc.args[0]), position) from exc
    # Scanner slices handle AS/dollar-quoted bodies, but SQL-standard BEGIN ATOMIC
    # semicolons belong to the function grammar, not to separate declarations.
    standard_body = any(
        isinstance(raw.stmt, ast.CreateFunctionStmt) and raw.stmt.sql_body is not None
        for raw in statements
    )
    slices = split(sql, with_parser=standard_body, only_slices=True)
    return PreparedSQL(source, sql, statements, slices, version("pglast"))
