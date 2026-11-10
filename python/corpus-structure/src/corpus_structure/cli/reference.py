"""Version-coupled native Typer 0.28 command reference production."""

from contextlib import ExitStack

import typer
from typer.cli import get_docs_for_click
from typer.core import TyperGroup
from typer.main import get_command


def command_markdown(app: typer.Typer, tokens: tuple[str, ...] = ()) -> str:
    """Resolve external names without parsing operands or invoking callbacks."""
    command = get_command(app)
    names = ["ci"]
    with ExitStack() as contexts:
        context = typer.Context(command, info_name="ci")
        contexts.enter_context(context)
        for token in tokens:
            child = command.get_command(context, token) if isinstance(command, TyperGroup) else None
            if child is None:
                raise typer.BadParameter(
                    f"unknown command {token!r} after {' '.join(names)!r}", param_hint="COMMAND"
                )
            command = child
            names.append(token)
            context = typer.Context(command, parent=context, info_name=token)
            contexts.enter_context(context)
        return get_docs_for_click(obj=command, ctx=context, name=" ".join(names)).rstrip() + "\n"
