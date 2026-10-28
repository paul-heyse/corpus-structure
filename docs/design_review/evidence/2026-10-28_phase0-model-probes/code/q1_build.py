"""Q-1 step 1: patch a copy of S4's core.yaml (code/q1/model_patch.yaml), lint it, generate the shapes.

Writes results/q1/schema/core_stage_b.yaml, results/q1/schema/core_stage_b.lint.json and
results/q1/generated/core_shapes.py.
"""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path

import yaml

HERE = Path(__file__).resolve().parent
FOLDER = HERE.parent
REPO = FOLDER.parents[3]
S4_CORE = REPO / "docs/design_review/evidence/2026-10-28_design-spikes/results/s4/schema/domains/core/schema/core.yaml"
OUT = FOLDER / "results/q1"
sys.path.insert(0, str(HERE / "q1"))


def patched() -> dict:
    core = yaml.safe_load(S4_CORE.read_text())
    patch = yaml.safe_load((HERE / "q1/model_patch.yaml").read_text())
    core["types"] = {**(core.get("types") or {}), **patch["types"]}
    core["enums"].update(patch["enums"])
    classes = {**core["classes"], **patch["classes"]}
    order = patch["class_order"]
    core["classes"] = {k: classes[k] for k in order} | {k: v for k, v in classes.items() if k not in order}
    for slot, anns in patch.get("slot_annotations", {}).items():
        core["slots"][slot].setdefault("annotations", {}).update(anns)
    core["description"] = "Q-1 probe copy of S4's core.yaml with code/q1/model_patch.yaml applied."
    return core


def main() -> int:
    (OUT / "schema").mkdir(parents=True, exist_ok=True)
    (OUT / "generated").mkdir(parents=True, exist_ok=True)
    target = OUT / "schema/core_stage_b.yaml"
    target.write_text(yaml.safe_dump(patched(), sort_keys=False, allow_unicode=True, width=110))
    shutil.copy(FOLDER / "results/q2/schema/.linkmllint.yaml", OUT / "schema/.linkmllint.yaml")
    lint_out = OUT / "schema/core_stage_b.lint.json"
    subprocess.run([str(Path(sys.executable).parent / "linkml-lint"), "--config", str(OUT / "schema/.linkmllint.yaml"),
                    "--format", "json", "-o", str(lint_out), str(target)], capture_output=True, text=True)
    problems = json.loads(lint_out.read_text() or "[]")
    for p in problems:
        p.pop("file", None)
    lint_out.write_text(json.dumps(problems, indent=1, sort_keys=True) + "\n")
    print("lint:", [f"{p['level']} {p['rule_name']}: {p['message']}" for p in problems])
    from stage_b import generate
    code = generate(target)
    (OUT / "generated/core_shapes.py").write_text(code)
    print("generated", len(code.splitlines()), "lines")
    return 0


if __name__ == "__main__":
    sys.exit(main())
