"""Complete Lark token positions for the math runner's native worker transport.

Keep this initializer lightweight: lifecycle controls have short submission budgets
and must not import the product's grammar, symbolic or NLP preparation at startup.
"""

from multiprocessing.reduction import register

from lark import Token


def _reduce_token(token: Token) -> tuple[type[Token], tuple[object, ...]]:
    # Lark 1.3.1's default reduction omits end positions used by extraction.
    return Token, (
        token.type,
        token.value,
        token.start_pos,
        token.line,
        token.column,
        token.end_line,
        token.end_column,
        token.end_pos,
    )


def configure_worker_transport() -> None:
    # The public multiprocessing registry is process-wide, separate from ordinary
    # pickle. Install only when running page work and in spawned workers. Keep this
    # idempotent registration stable: private dispatch restoration races other pools.
    register(Token, _reduce_token)
