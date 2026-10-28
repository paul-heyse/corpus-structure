"""Registration entries for `ci` groups whose owning document has not built them yet.

Each owner replaces its entry in `cli.REGISTRY` with its module's `register` (coordinator
decision 10). A planned entry appears in `ci --help` and exits 1 naming its owner.
"""

from __future__ import annotations

from dataclasses import dataclass

import typer

from corpus_structure.cli.output import stderr_console


@dataclass(frozen=True)
class Planned:
    name: str
    help: str
    owner: str

    def register(self, app: typer.Typer) -> None:
        def stub() -> None:
            stderr_console().print(f"ci {self.name}: not built yet (owner: {self.owner})")
            raise typer.Exit(code=1)

        app.command(
            self.name,
            help=f"{self.help} [not built yet: {self.owner}]",
            context_settings={"allow_extra_args": True, "ignore_unknown_options": True},
        )(stub)
