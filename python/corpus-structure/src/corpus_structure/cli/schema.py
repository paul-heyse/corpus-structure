"""Compile the real composed semantic release without acquiring a database."""

from __future__ import annotations

from pathlib import Path
from typing import Annotated

import typer
from pydantic import BaseModel
from rich.table import Table

from corpus_structure.cli.output import JsonOpt, emit
from corpus_structure.cli.query import refusal

schema_app = typer.Typer(help="Compile a composed semantic release.", no_args_is_help=True)


class ArtifactRow(BaseModel):
    kind: str
    hash: str


class CompileResult(BaseModel):
    packs: list[str]
    release_id: str
    execution_model_id: str | None
    artifacts: list[ArtifactRow]


def _render(result):
    table = Table("kind", "hash", title=f"semantic release {result.release_id}")
    for artifact in result.artifacts:
        table.add_row(artifact.kind, artifact.hash)
    return table


@schema_app.command("compile")
def compile_(
    domain: Annotated[list[str] | None, typer.Option("--domain")] = None,
    domains: Annotated[Path, typer.Option("--domains")] = Path("domains"),
    out: Annotated[Path | None, typer.Option("--out")] = None,
    json_: JsonOpt = False,
):
    from corpus_structure.semantic.regeneration import prepare_packs

    domain = domain or ["statistics"]
    with refusal(json_):
        if any(Path(name).name != name for name in domain):
            raise ValueError("domain must name a pack under --domains")
        bundle, _deps, _profile, prepared = prepare_packs(tuple(domains / name for name in domain))
        if out is not None:
            out.mkdir(parents=True, exist_ok=True)
            (out / "manifest.json").write_bytes(prepared.manifest)
            for artifact in prepared.artifacts:
                (out / (artifact.kind.replace("/", "_") + ".artifact")).write_bytes(
                    artifact.content
                )
            for source in bundle.sources:
                target = out / "sources" / (source.name.replace("/", "_") + ".yaml")
                target.parent.mkdir(exist_ok=True)
                target.write_bytes(source.content)
        emit(
            CompileResult(
                packs=domain,
                release_id=prepared.release_id,
                execution_model_id=prepared.execution_model_id,
                artifacts=[ArtifactRow(kind=a.kind, hash=a.digest) for a in prepared.artifacts],
            ),
            json=json_,
            render=_render,
        )


@schema_app.command("check")
def check_(
    ctx: typer.Context,
    domain: Annotated[list[str] | None, typer.Option("--domain")] = None,
    release: Annotated[str | None, typer.Option("--release")] = None,
    domains: Annotated[Path, typer.Option("--domains")] = Path("domains"),
    json_: JsonOpt = False,
):
    """Check candidate packs or fully verify an archived release without changing it."""
    if release is None:
        return compile_(domain or ["statistics"], domains, None, json_)
    from corpus_structure.cli.output import state
    from corpus_structure.semantic.releases import verify_release
    from corpus_structure.semantic.runtime import open_runtime_engine

    with refusal(json_):
        if domain is not None:
            raise ValueError("select either --domain or --release")
        with (
            open_runtime_engine(state(ctx).settings(), "ci-schema-check", purpose="read") as engine,
            engine.connect() as conn,
            conn.begin(),
        ):
            conn.exec_driver_sql("SET TRANSACTION READ ONLY")
            prepared = verify_release(conn, release)
        emit(
            CompileResult(
                packs=[],
                release_id=prepared.release_id,
                execution_model_id=prepared.execution_model_id,
                artifacts=[ArtifactRow(kind=a.kind, hash=a.digest) for a in prepared.artifacts],
            ),
            json=json_,
            render=_render,
        )


@schema_app.command("derive")
def derive_(
    out: Annotated[Path, typer.Option("--out")],
    domain: Annotated[list[str] | None, typer.Option("--domain")] = None,
    domains: Annotated[Path, typer.Option("--domains")] = Path("domains"),
    json_: JsonOpt = False,
):
    """Emit reviewed candidate products to a new directory; never deploy or overwrite history."""
    with refusal(json_):
        if out.exists():
            raise ValueError("derivation requires a new --out directory")
        compile_(domain, domains, out, json_)
        from corpus_structure.semantic.native_products import closure_products, physical_products

        native = out / "native"
        native.mkdir()
        bootstrap = native / "bootstrap"
        bootstrap.mkdir()
        for product in physical_products():
            (bootstrap / (product.name.replace("/", "_") + ".sql")).write_bytes(product.content)
        for product in closure_products():
            (native / product.name).write_bytes(product.content)


def register(app: typer.Typer):
    app.add_typer(schema_app, name="schema")
