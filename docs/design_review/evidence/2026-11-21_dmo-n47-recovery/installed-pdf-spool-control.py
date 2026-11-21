"""Run the installed command with one parent-only fault or assertion."""
import ast
import runpy
import sys
from pathlib import Path

mode = sys.argv[1]
assert mode in {"interrupt", "no-provider"}
entrypoint = Path(sys.executable).with_name("ci")
sys.argv = [str(entrypoint), *sys.argv[2:]]
path = Path("python/corpus-structure/src/corpus_structure/orchestrate/pdf_streaming.py")
tree = ast.parse(path.read_bytes())
producer = next(
    node
    for node in tree.body
    if isinstance(node, ast.FunctionDef) and node.name == "run_private_native_pdf_build"
)
matches = [
    node.lineno
    for node in ast.walk(producer)
    if isinstance(node, ast.Assign)
    and len(node.targets) == 1
    and isinstance(node.targets[0], ast.Name)
    and node.targets[0].id == "fresh_entries"
]
assert len(matches) == 1
tool = 3
monitor = sys.monitoring
monitor.use_tool_id(tool, "dmo-installed-pdf-control")


def line(code, number):
    if number == matches[0]:
        monitor.set_local_events(tool, code, 0)
        raise OSError("DMO control interrupted after durable PDF spool completion")


def start(code, offset):
    if mode == "interrupt" and (
        code.co_filename.endswith("/orchestrate/pdf_streaming.py")
        and code.co_name == producer.name
    ):
        monitor.set_local_events(tool, code, monitor.events.LINE)
    elif mode == "no-provider" and (
        code.co_filename.endswith("/ingest/pdf_worker.py")
        and code.co_qualname == "PdfWorker.stream"
    ):
        raise AssertionError("DMO recovery started a PDF provider")
    return monitor.DISABLE


monitor.register_callback(tool, monitor.events.LINE, line)
monitor.register_callback(tool, monitor.events.PY_START, start)
monitor.set_events(tool, monitor.events.PY_START)
try:
    runpy.run_path(str(entrypoint), run_name="__main__")
finally:
    monitor.free_tool_id(tool)
