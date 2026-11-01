"""Disposable Typer/Rich/native file-export composition, not production ci acceptance."""
import json
import logging
import os
import subprocess
import sys
import tempfile
from pathlib import Path

if '--child' in sys.argv:
    import typer
    from opentelemetry.exporter.otlp.json.file import FileSpanExporter
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import SimpleSpanProcessor
    from rich.console import Console
    from rich.live import Live
    from rich.logging import RichHandler

    app = typer.Typer(pretty_exceptions_show_locals=False)
    @app.command()
    def operation():
        with tempfile.TemporaryDirectory() as tmp:
            provider = TracerProvider(shutdown_on_exit=False)
            provider.add_span_processor(SimpleSpanProcessor(FileSpanExporter(Path(tmp) / 'spans.jsonl')))
            console = Console(stderr=True, color_system=None)
            logger = logging.getLogger('synthetic')
            logger.handlers = [RichHandler(console=console, show_path=False)]
            logger.propagate = False
            logger.setLevel(logging.INFO)
            with provider.get_tracer('probe').start_as_current_span('synthetic'), Live('working', console=console, redirect_stdout=False, transient=True):
                logger.warning('synthetic warning')
                print(json.dumps({'result': 'ok'}))
            provider.shutdown()
            assert 'synthetic' in (Path(tmp) / 'spans.jsonl').read_text()
    sys.argv = [sys.argv[0]]
    app()
else:
    env = {k: v for k, v in os.environ.items() if not k.startswith(('OTEL_', 'LOGFIRE_', 'CORPUS_'))}
    result = subprocess.run([sys.executable, __file__, '--child'], env=env, capture_output=True, text=True, timeout=10)
    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout) == {'result': 'ok'}
    assert 'synthetic warning' in result.stderr
    print(json.dumps({'outcome': 'passed', 'stdout': 'result-only JSON', 'stderr': 'Rich warning', 'span_file': 'native exported', 'scope': 'disposable app; production ci not_run'}))
