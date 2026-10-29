"""Compile the real composed semantic release without acquiring a database."""
from __future__ import annotations
import json
from pathlib import Path
from typing import Annotated
import typer
from pydantic import BaseModel
from rich.table import Table
from corpus_structure.cli.output import JsonOpt, emit
from corpus_structure.cli.query import refusal
schema_app=typer.Typer(help="Compile a composed semantic release.",no_args_is_help=True)
class ArtifactRow(BaseModel):
    kind:str
    hash:str
class CompileResult(BaseModel):
    packs:list[str]
    release_id:str
    execution_model_id:str|None
    artifacts:list[ArtifactRow]
def _render(result):
    table=Table("kind","hash",title=f"semantic release {result.release_id}")
    for artifact in result.artifacts: table.add_row(artifact.kind,artifact.hash)
    return table
@schema_app.command("compile")
def compile_(domain:Annotated[list[str],typer.Option("--domain")]=["statistics"],domains:Annotated[Path,typer.Option("--domains")]=Path("domains"),out:Annotated[Path|None,typer.Option("--out")]=None,json_:JsonOpt=False):
    from corpus_structure.semantic.regeneration import prepare_packs
    with refusal(json_):
        if any(Path(name).name != name for name in domain): raise ValueError("domain must name a pack under --domains")
        bundle,deps,profile,prepared=prepare_packs(tuple(domains/name for name in domain))
        if out is not None:
            out.mkdir(parents=True,exist_ok=True)
            (out/"manifest.json").write_bytes(prepared.manifest)
            for artifact in prepared.artifacts: (out/(artifact.kind.replace("/","_")+".artifact")).write_bytes(artifact.content)
            for source in bundle.sources:
                target=out/"sources"/(source.name.replace("/","_")+".yaml")
                target.parent.mkdir(exist_ok=True)
                target.write_bytes(source.content)
        emit(CompileResult(packs=domain,release_id=prepared.release_id,execution_model_id=prepared.execution_model_id,artifacts=[ArtifactRow(kind=a.kind,hash=a.digest) for a in prepared.artifacts]),json=json_,render=_render)
def register(app:typer.Typer): app.add_typer(schema_app,name="schema")
