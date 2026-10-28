"""P4: Typer 0.27.3 + Rich 15.0.0 + pydantic-settings 2.16.1 for the ``ci`` shape of D8 §4.

Questions:
  a. With command groups mounted by ``add_typer`` and a root callback that builds settings once
     into ``ctx.obj``, does ``CliRunner`` keep stdout (data, ``--json``) and stderr (diagnostics)
     apart?
  b. Does a module-level Rich ``Console()`` follow CliRunner's stream swap (file resolved at write
     time), and at what width does it render when not a TTY?
  c. Settings: env prefix + nested delimiter, init-kwarg override, ``_env_file=None``,
     ``settings_cached()`` identity, ``SecretStr`` masking; does an unknown prefixed variable
     raise with ``extra="forbid"``?

Run (spike venv):
    build/spike-venv/bin/python -I probes/p4_typer_cli.py
"""

from __future__ import annotations

import json
import os
from typing import Annotated

import typer
from pydantic import BaseModel, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict
from rich.console import Console
from rich.table import Table
from typer.testing import CliRunner


class DatabaseSettings(BaseModel):
    url: str = "postgresql:///corpus"
    pool_max: int = 4


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="CORPUS_", env_nested_delimiter="__", extra="forbid")
    database: DatabaseSettings = DatabaseSettings()
    data_dir: str = "build/data"
    vllm_endpoint: str = "http://127.0.0.1:8000/v1"
    api_key: SecretStr | None = None


out_console = Console()  # module level, file=None
err_console = Console(stderr=True)

app = typer.Typer(no_args_is_help=True, pretty_exceptions_enable=False, add_completion=False)
db_app = typer.Typer(help="Database")
app.add_typer(db_app, name="db")

JsonOpt = Annotated[bool, typer.Option("--json", help="Machine-readable output on stdout")]


class Status(BaseModel):
    run: str
    awaiting_agent: int
    db_url: str


@app.callback()
def root(ctx: typer.Context) -> None:
    ctx.obj = Settings()


@app.command()
def status(ctx: typer.Context, run: str = "latest", json_: JsonOpt = False) -> None:
    s: Settings = ctx.obj
    result = Status(run=run, awaiting_agent=3, db_url=s.database.url)
    err_console.print("[dim]connecting...[/dim]")
    if json_:
        typer.echo(result.model_dump_json())
        return
    t = Table("run", "awaiting_agent", "db")
    t.add_row(result.run, str(result.awaiting_agent), result.db_url)
    out_console.print(t)
    out_console.print(f"width={out_console.width}")


@db_app.command("migrate")
def migrate() -> None:
    err_console.print("migrating")


def main() -> None:
    r = CliRunner()
    res: dict = {}
    os.environ["CORPUS_DATABASE__URL"] = "postgresql:///ci_test_1"
    a = r.invoke(app, ["status", "--json"])
    res["json"] = {"exit": a.exit_code, "stdout_parses": _parses(a.stdout), "stderr": a.stderr.strip()}
    b = r.invoke(app, ["status"])
    res["rich"] = {"exit": b.exit_code, "table_on_stdout": "awaiting_agent" in b.stdout,
                   "width_line": [x for x in b.stdout.splitlines() if x.startswith("width=")],
                   "stderr": b.stderr.strip()}
    res["group"] = {"exit": r.invoke(app, ["db", "migrate"]).exit_code}
    g = r.invoke(app, ["--json", "status"])
    res["root_level_flag_rejected"] = {"exit": g.exit_code, "msg": g.output.strip().splitlines()[-2:]}

    # settings behaviour
    res["settings"] = {"env_nested": Settings().database.url}
    res["settings"]["init_override"] = Settings(database={"url": "postgresql:///other"}).database.url
    os.environ["CORPUS_API_KEY"] = "s3cret"
    res["settings"]["secret_repr"] = repr(Settings().api_key)
    os.environ["CORPUS_DATA_DIRR"] = "typo"
    try:
        Settings()
        res["settings"]["unknown_prefixed_env_var"] = "ignored silently"
    except Exception as e:  # noqa: BLE001
        res["settings"]["unknown_prefixed_env_var"] = f"raised {type(e).__name__}"
    res["settings"]["cached_identity"] = Settings.settings_cached() is Settings.settings_cached()
    Settings.settings_clear_cache()
    print(json.dumps(res, indent=1))


def _parses(s: str) -> bool:
    try:
        json.loads(s)
        return True
    except ValueError:
        return False


if __name__ == "__main__":
    main()
