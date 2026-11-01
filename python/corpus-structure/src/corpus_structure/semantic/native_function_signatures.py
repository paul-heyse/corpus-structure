"""PostgreSQL function identity comes from input-bearing AST parameters only."""

from pglast import ast, enums
from pglast.stream import RawStream
from sqlalchemy.dialects.postgresql import dialect


def qualified_name(parts) -> str:
    quote = dialect(paramstyle="named").identifier_preparer.quote
    return ".".join(quote(part.sval) for part in parts or ())


def function_signature(statement: ast.CreateFunctionStmt, *, include_outputs=False) -> str:
    output_modes = {
        enums.FunctionParameterMode.FUNC_PARAM_OUT,
        enums.FunctionParameterMode.FUNC_PARAM_TABLE,
    }
    return (
        qualified_name(statement.funcname)
        + "("
        + ",".join(
            RawStream()(parameter.argType)
            for parameter in statement.parameters or ()
            if include_outputs or parameter.mode not in output_modes
        )
        + ")"
    )


def remove_output_signature_aliases(functions, statements):
    """Retire only aliases exposed by OUT/TABLE declarations, preserving real overloads."""
    declarations = [
        item.stmt for item in statements if isinstance(item.stmt, ast.CreateFunctionStmt)
    ]
    actual = {function_signature(statement) for statement in declarations}
    for statement in declarations:
        previous = function_signature(statement, include_outputs=True)
        if previous != function_signature(statement) and previous not in actual:
            functions.pop(previous, None)
