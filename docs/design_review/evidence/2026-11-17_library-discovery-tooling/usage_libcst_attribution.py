import libcst as cst
from libcst.metadata import MetadataWrapper, QualifiedNameProvider
src = '''
import typer as t
import pydantic
from pydantic import BaseModel as BM, Field
from .models import Reexported
from . import models
import importlib
class A(BM): x: int = Field(default=1, alias="y")
class B(pydantic.BaseModel): pass
app = t.Typer(no_args_is_help=True)
alias = t.Option
def f():
    from rich.console import Console
    c = Console(stderr=True)
    o = alias("--x", help="h")
    return c
Reexported(); models.Thing()
dyn = importlib.import_module("yaml"); getattr(dyn, "safe_load")("x")
lazy = t
lazy.Argument()
@app.command(name="go")
def go(): ...
'''
class V(cst.CSTVisitor):
    METADATA_DEPENDENCIES=(QualifiedNameProvider,)
    def visit_Call(self, n):
        print(f"{cst.Module([]).code_for_node(n.func):28} -> {sorted((q.name, q.source.name) for q in self.get_metadata(QualifiedNameProvider, n.func, set()))}")
    def visit_Arg(self, n):
        pass
MetadataWrapper(cst.parse_module(src)).visit(V())
