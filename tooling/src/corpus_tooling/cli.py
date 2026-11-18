"""Root of the `tooling` command."""

import typer

app = typer.Typer(add_completion=False, no_args_is_help=True, pretty_exceptions_show_locals=False)


@app.callback()
def root() -> None:
    """Repository tooling separate from the product."""


def main() -> None:
    app()
