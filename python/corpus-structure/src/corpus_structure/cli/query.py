"""Thin typed-query CLI adapter (D8 §4–§5)."""
from __future__ import annotations
import json as jsonlib
from contextlib import contextmanager
from typing import Annotated,Any
import typer
from pydantic import ValidationError
from sqlalchemy import text
from corpus_structure.cli.output import JsonOpt,emit,state,stderr_console
from corpus_structure.cli.orchestrate import ENGINE
from corpus_structure.serve.journey import QueryRefused,serve_query,select_run
from corpus_structure.serve.queries import GENERIC
from corpus_structure.serve.registry import build_registry,QueryRegistryError

@contextmanager
def refusal(json:bool):
    try: yield
    except (QueryRefused,QueryRegistryError,ValidationError,ValueError,LookupError) as e:
        if json:
            typer.echo(jsonlib.dumps({'error':{'code':type(e).__name__,'message':str(e)}}))
        else: stderr_console().print(f'refused: {e}')
        raise typer.Exit(1) from None

def context(conn:Any,project:str|None,run:str)->tuple[int,int,Any]:
    from corpus_structure.orchestrate.commands import project_id
    from corpus_structure.schema.pack import DOMAINS
    pid,_=project_id(conn,project)
    rid=select_run(conn,pid,run if run=='promoted' else int(run))
    domain=conn.execute(text('SELECT domain FROM meta.project WHERE id=:p'),{'p':pid}).scalar_one()
    return pid,rid,build_registry(GENERIC,DOMAINS/domain)

def query(ctx:typer.Context,name:Annotated[str,typer.Argument()],run:str='promoted',project:str|None=None,param:Annotated[list[str]|None,typer.Option('--param')]=None,page_token:str|None=None,max_rows:int|None=None,max_chars:int|None=None,json:JsonOpt=False)->None:
    params={}
    with refusal(json):
        for pair in param or []:
            if '=' not in pair: raise QueryRefused('--param needs NAME=VALUE')
            key,value=pair.split('=',1)
            if key in params: raise QueryRefused(f'duplicate parameter {key}')
            try: params[key]=jsonlib.loads(value)
            except ValueError: params[key]=value
        with ENGINE(state(ctx).settings()) as engine,engine.connect() as conn:
            conn.execute(text('SET TRANSACTION READ ONLY'))
            pid,_,registry=context(conn,project,run)
            result=serve_query(conn,registry,name,params,project_id=pid,run=run if run=='promoted' else int(run),page_token=page_token,max_rows=max_rows,max_chars=max_chars)
            emit(result,json=json)

def register(app:typer.Typer)->None:
    app.command('query')(query)
