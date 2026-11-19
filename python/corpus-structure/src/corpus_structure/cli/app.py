"""Explicit full-tree construction and first-command installed dispatch (D8 §4)."""

from __future__ import annotations

import os
import sys
from functools import cache
from importlib import import_module

import typer

from corpus_structure.cli import REGISTRY, CommandRegistration
from corpus_structure.cli.output import CliState


def root(ctx: typer.Context) -> None:
    """corpus-structure: build and query a structured representation of a corpus."""
    if ctx.obj is None:
        ctx.obj = CliState()
    from corpus_structure.model.compiled import model_request_scope
    from corpus_structure.orchestrate.execution_host import execution_host_scope

    ctx.with_resource(model_request_scope())
    ctx.with_resource(execution_host_scope())


@cache
def _registered(entry: CommandRegistration) -> typer.Typer:
    # Registration functions may extend module-owned subgroups. Run each once,
    # then reuse its declarations when constructing partial or complete roots.
    registered = typer.Typer()
    module = import_module("corpus_structure.cli." + entry.module)
    getattr(module, entry.function)(registered)
    return registered


def _build(entries: tuple[CommandRegistration, ...]) -> typer.Typer:
    app = typer.Typer(
        name="ci",
        help="corpus-structure: build and query a structured representation of a corpus.",
        no_args_is_help=True,
        add_completion=True,
        pretty_exceptions_show_locals=False,
    )
    app.callback()(root)
    for entry in entries:
        registered = _registered(entry)
        app.registered_commands.extend(registered.registered_commands)
        app.registered_groups.extend(registered.registered_groups)
    return app


@cache
def build_full_app() -> typer.Typer:
    """Build the complete installed tree for help, completion and reference consumers."""
    return _build(REGISTRY)


def build_command_app(arguments: list[str]) -> typer.Typer:
    """Select a declared root family, retaining full Typer handling for global modes."""
    names = {name for entry in REGISTRY for name in entry.names}
    if (
        not arguments
        or arguments[0] not in names
        or any(
            argument in {"--help", "--install-completion", "--show-completion"}
            for argument in arguments
        )
        or "_CI_COMPLETE" in os.environ
    ):
        return build_full_app()
    return _build(tuple(entry for entry in REGISTRY if arguments[0] in entry.names))


def main() -> None:
    arguments = sys.argv[1:]
    if arguments[:1] == ["test"] and "--" in arguments:
        boundary = arguments.index("--")
        app = build_command_app(arguments[:boundary])
        app(args=arguments[:boundary], obj=CliState(test_args=tuple(arguments[boundary + 1 :])))
    else:
        build_command_app(arguments)(args=arguments)
