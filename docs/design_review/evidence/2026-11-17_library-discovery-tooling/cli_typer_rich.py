import io, json, sys, os
from typing import Annotated
import typer
from typer.testing import CliRunner
from rich.console import Console
from rich.table import Table
from rich.json import JSON
from rich.progress import Progress

app = typer.Typer(no_args_is_help=True)
scan = typer.Typer()
app.add_typer(scan, name="usage")

@app.callback()
def root(ctx: typer.Context, project: Annotated[str, typer.Option("--project")] = "."):
    ctx.obj = {"project": project}

@scan.command("census")
def census(ctx: typer.Context, json_: Annotated[bool, typer.Option("--json")] = False,
           hits: int = 0, limit: int = 2):
    Console(stderr=True).print("diag: scanning")
    payload = {"project": ctx.find_root().obj["project"], "hits": list(range(hits))[:limit],
               "truncated": hits > limit}
    if json_:
        sys.stdout.write(json.dumps(payload) + "\n")
    else:
        Console().print(payload)
    if hits == 0:
        raise typer.Exit(code=1)

r = CliRunner()
for args in (["--project", "p", "usage", "census", "--json", "--hits", "5"],
             ["--project", "p", "usage", "census", "--json"],
             ["usage", "census", "--project", "p"],
             ["usage", "census", "--bogus"]):
    res = r.invoke(app, args)
    print("ARGS", args, "exit", res.exit_code, "| stdout:", repr(res.stdout[:120]), "| stderr:", repr(res.stderr[:160]))

# Rich table on a non-terminal 80-col console with a long identifier
buf = io.StringIO()
c = Console(file=buf, width=40)
print("non-tty is_terminal", c.is_terminal, "color_system", c.color_system)
t = Table("id", "where")
t.add_row("python/corpus-structure/src/corpus_structure/cli/output.py::emit_something_long", "x")
c.print(t)
print(buf.getvalue())
buf = io.StringIO(); c = Console(file=buf, width=40)
t = Table("id", "where", box=None)
t.add_column  # noop
t2 = Table(box=None, show_header=True); t2.add_column("id", no_wrap=True); t2.add_column("where")
t2.add_row("python/corpus-structure/src/corpus_structure/cli/output.py::emit_something_long", "x")
c.print(t2); print("NO_WRAP:", repr(buf.getvalue()))
# JSON allow_nan default
print("JSON nan:", JSON.from_data({"x": float("nan")}).text.plain)
# default Console width when piped & no COLUMNS
os.environ.pop("COLUMNS", None)
print("piped default width", Console(file=io.StringIO()).width)
# Progress on non-interactive stderr console
buf = io.StringIO(); pc = Console(file=buf)
with Progress(console=pc, redirect_stdout=False, transient=True) as p:
    tid = p.add_task("scan", total=3)
    for _ in range(3): p.advance(tid)
print("progress non-tty transient output:", repr(buf.getvalue()))
buf = io.StringIO(); pc = Console(file=buf)
with Progress(console=pc, redirect_stdout=False) as p:
    tid = p.add_task("scan", total=3)
    for _ in range(3): p.advance(tid)
print("progress non-tty non-transient output:", repr(buf.getvalue()[:200]))
# record export
rc = Console(record=True, file=io.StringIO(), width=60)
rc.print(Table("a","b")); txt = rc.export_text(); print("export_text styles=False has ESC:", "\x1b" in txt, "| second export empty:", rc.export_text()=="")
