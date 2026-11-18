"""Root of the `tooling` command (ADR-0132): read-only repository tooling, separate from the
product. Groups are attached with explicit names; an unnamed merge would drop the group callback."""

import typer

from corpus_tooling.library.app import app as library_app

app = typer.Typer(add_completion=False, no_args_is_help=True, pretty_exceptions_show_locals=False)


@app.callback()
def root() -> None:
    """Repository tooling separate from the product."""


app.add_typer(library_app, name="library")


def main() -> None:
    app()
