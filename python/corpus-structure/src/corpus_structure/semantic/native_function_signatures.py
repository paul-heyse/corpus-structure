"""PostgreSQL function identity comes from input-bearing AST parameters only."""

from pglast import ast, enums
from pglast.stream import RawStream


def function_signature(statement: ast.CreateFunctionStmt, *, include_outputs=False) -> str:
    output_modes = {
        enums.FunctionParameterMode.FUNC_PARAM_OUT,
        enums.FunctionParameterMode.FUNC_PARAM_TABLE,
    }
    return (
        ".".join(part.sval for part in statement.funcname or ())
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
