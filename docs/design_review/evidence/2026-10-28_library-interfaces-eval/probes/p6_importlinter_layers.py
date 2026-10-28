"""P6: import-linter 2.15 layers contract for D9 §1's dependency direction.

Builds a throwaway skeleton of ``corpus_structure`` in a temporary directory (empty modules plus
the imports named below), writes a ``pyproject.toml`` ``[tool.importlinter]`` contract and runs
``lint-imports`` three times:

  1. D9 §1 as written: top tier ``evaluate | intervene | serve`` (independent siblings), with only
     downward imports -> expected to pass;
  2. the same contract after ``intervene`` imports ``serve.queries`` (the MCP ``query``/``explain``
     tools of D8 §2.4 call the typed queries of D8 §5) -> expected to fail;
  3. an alternative layering that separates the entry points (``cli : intervene``) from the
     shared application layer ``serve`` -> expected to pass with that import.

Run (scratch venv holding import-linter==2.15):
    $VENV/bin/python -I probes/p6_importlinter_layers.py
"""

from __future__ import annotations

import os
import subprocess
import sys
import tempfile
import textwrap
from pathlib import Path

PKGS = ["core", "schema", "ingest", "methods", "consolidate", "validate", "orchestrate",
        "evaluate", "intervene", "serve", "cli"]

D9_LAYERS = ["evaluate | intervene | serve", "orchestrate", "validate", "consolidate",
             "ingest | methods", "schema", "core"]
ALT_LAYERS = ["cli : intervene", "evaluate | serve", "orchestrate", "validate", "consolidate",
              "ingest | methods", "schema", "core"]

BASE_IMPORTS = {
    "schema": ["core"], "ingest": ["schema"], "methods": ["schema"], "consolidate": ["methods"],
    "validate": ["consolidate"], "orchestrate": ["validate", "ingest"],
    "evaluate": ["orchestrate"], "serve": ["orchestrate"], "intervene": ["orchestrate"],
}


def build(root: Path, imports: dict[str, list[str]]) -> None:
    pkg = root / "src" / "corpus_structure"
    for p in PKGS:
        (pkg / p).mkdir(parents=True, exist_ok=True)
        body = "".join(f"import corpus_structure.{d}\n" for d in imports.get(p, []))
        (pkg / p / "__init__.py").write_text(body)
    (pkg / "__init__.py").write_text("")


def contract(layers: list[str], exhaustive: bool) -> str:
    lines = ",\n    ".join(f'"{x}"' for x in layers)
    return textwrap.dedent(f"""\
        [tool.importlinter]
        root_package = "corpus_structure"

        [[tool.importlinter.contracts]]
        name = "D9 §1 dependency direction"
        type = "layers"
        containers = ["corpus_structure"]
        layers = [
            {lines}
        ]
        exhaustive = {"true" if exhaustive else "false"}
        exhaustive_ignores = ["cli"]
        """)


def run(title: str, imports: dict, layers: list[str], exhaustive: bool = False) -> None:
    with tempfile.TemporaryDirectory() as d:
        root = Path(d)
        build(root, imports)
        (root / "pyproject.toml").write_text(contract(layers, exhaustive))
        env = dict(os.environ, PYTHONPATH=str(root / "src"))
        lint = Path(sys.executable).with_name("lint-imports")
        p = subprocess.run([str(lint), "--no-cache"], cwd=root, env=env, capture_output=True, text=True)
        tail = [x for x in p.stdout.splitlines() if x.strip()][-6:]
        print(f"== {title}: exit {p.returncode}")
        print("\n".join("   " + x for x in tail))


if __name__ == "__main__":
    run("1 D9 as written, downward imports only", BASE_IMPORTS, D9_LAYERS)
    with_query = {**BASE_IMPORTS, "intervene": ["orchestrate", "serve"], "cli": ["serve", "evaluate", "intervene"]}
    run("2 D9 as written, intervene imports serve", with_query, D9_LAYERS)
    run("3 entry points above serve (cli : intervene)", with_query, ALT_LAYERS, exhaustive=True)
