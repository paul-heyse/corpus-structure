"""`ci schema compile` (schema and rules, P0-S-1; D8 §4).

Compiles a domain pack from disk over the installed model and shows the schema version and each
artifact's identity and hash; `--out DIR` also writes the artifacts (a text artifact as its text,
the others as JSON). It reads no settings and no database. `ci schema diff` waits for phase 1.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Annotated

import typer
from pydantic import BaseModel
from rich.console import RenderableType
from rich.table import Table

from corpus_structure.cli.output import JsonOpt, emit, stderr_console

schema_app = typer.Typer(
    help="Compile the pack; diff schema versions (phase 1).", no_args_is_help=True
)


class ArtifactRow(BaseModel):
    compiler: str
    compiler_version: str
    kind: str
    hash: str


class CompileResult(BaseModel):
    packs: list[str]
    schema_version: str
    model_revision: str
    artifacts: list[ArtifactRow]


def _render(result: BaseModel) -> RenderableType:
    assert isinstance(result, CompileResult)
    table = Table(
        "compiler",
        "version",
        "kind",
        "hash",
        title=f"schema version {result.schema_version[:12]} ({', '.join(result.packs)})",
    )
    for a in result.artifacts:
        table.add_row(a.compiler, a.compiler_version, a.kind, a.hash[:16])
    return table


@schema_app.command("compile")
def compile_(
    domain: Annotated[list[str], typer.Option("--domain", help="A pack under --domains.")] = [  # noqa: B006
        "statistics"
    ],
    domains: Annotated[Path, typer.Option("--domains", help="The packs' root.")] = Path("domains"),
    out: Annotated[Path | None, typer.Option("--out", help="Write the artifacts here.")] = None,
    json_: JsonOpt = False,
) -> None:
    """Compile the packs into one schema version and show the artifacts' hashes."""
    from corpus_structure.schema.compile import compile_paths
    from corpus_structure.schema.pack import PackError

    try:
        compiled = compile_paths([domains / name for name in domain])
    except PackError as error:
        stderr_console().print("\n".join(error.problems))
        raise typer.Exit(code=1) from None
    if out is not None:
        out.mkdir(parents=True, exist_ok=True)
        for a in compiled.artifacts:
            name = f"{a.compiler}.{a.kind}"
            text = (
                a.body
                if isinstance(a.body, str)
                else json.dumps(a.body, indent=1, ensure_ascii=False)
            )
            (out / (name + (".md" if isinstance(a.body, str) else ".json"))).write_text(
                text, encoding="utf-8"
            )
    result = CompileResult(
        packs=[p.name for p in compiled.packs],
        schema_version=compiled.schema_version,
        model_revision=compiled.model_revision,
        artifacts=[
            ArtifactRow(
                compiler=a.compiler, compiler_version=a.compiler_version, kind=a.kind, hash=a.hash
            )
            for a in compiled.artifacts
        ],
    )
    emit(result, json=json_, render=_render)


def register(app: typer.Typer) -> None:
    app.add_typer(schema_app, name="schema")
