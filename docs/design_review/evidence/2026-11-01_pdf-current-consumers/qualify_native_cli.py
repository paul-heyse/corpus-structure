"""Exercise the installed CLI with the exact current source selection."""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--selection", type=Path, required=True)
    parser.add_argument("--database", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    selection = json.loads(args.selection.read_bytes())
    root = Path(__file__).resolve().parents[4]
    command = shutil.which("uv")
    if command is None:
        raise RuntimeError("uv is required for the actual application entry point")
    args.output.mkdir()
    receipts = []

    def checkpoint(outcome="partial"):
        filename = "result.json" if outcome == "passed" else "partial.json"
        (args.output / filename).write_text(
            json.dumps({"outcome": outcome, "selection": selection, "calls": receipts}, indent=2)
            + "\n"
        )

    def inspect(view, extra=(), *, wrong_digest=False):
        label = "wrong-digest" if wrong_digest else view
        argv = [
            command, "run", "ci", "source", "inspect", str(selection["run_id"]),
            "--producing-task", str(selection["task_id"]),
            "--product", selection["product_key"],
            "--native-digest", "0" * 64 if wrong_digest else selection["content_digest"],
            "--native-view", view, "--limit", "5", "--json", *extra,
        ]
        result = subprocess.run(
            argv, cwd=root,
            env=dict(os.environ, CORPUS_DATABASE__URL=args.database),
            capture_output=True, text=True, timeout=300, check=False,
        )
        (args.output / f"{label}.stdout.json").write_text(result.stdout)
        (args.output / f"{label}.stderr.txt").write_text(result.stderr)
        receipts.append({"argv": argv, "returncode": result.returncode})
        checkpoint()
        if wrong_digest:
            assert result.returncode != 0
            assert any(word in result.stdout + result.stderr for word in ("digest", "pin"))
        else:
            assert result.returncode == 0, result.stdout + result.stderr
            value = json.loads(result.stdout)
            assert value["version"] == 3
            assert value["selection"]["content_digest"] == selection["content_digest"]
            assert value["outcome"] == "source_ready"

    checkpoint()
    inspect("sections")
    inspect("formula", ("--pointer", selection["formula_pointer"]))
    inspect("cell", ("--pointer", selection["table_pointer"], "--cell", str(selection["cell_index"])))
    inspect("trace", ("--pointer", selection["formula_pointer"]))
    inspect("companion", ("--pointer", selection["formula_pointer"]))
    inspect("manifest", ("--collection", "coverage"))
    inspect("items", wrong_digest=True)
    checkpoint("passed")


if __name__ == "__main__":
    main()
