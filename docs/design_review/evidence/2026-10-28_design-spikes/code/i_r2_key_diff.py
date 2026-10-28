"""I-R2: which key forms move from the I-R1 instruments (tree form when parsed) to the token form.

    UV_PROJECT_ENVIRONMENT=$REPO/build/spike-venv uv run python code/i_r2_key_diff.py [--before 35ea59a]

Every math value and symbol of the batch sets the comparisons read (results/s0/reference,
trace_stored, stored/*; results/s0r2/reference_v1, stored/*): formula and set ``latex``, condition
operands, ``param_values`` entries, entity symbols and binding-map keys. Each is put in canonical
form by ``instruments.values`` (``canonical_latex`` / ``canonical_symbol``, with the unit's page
macros) twice: by the instruments at ``--before`` (extracted with ``git archive`` into a temporary
directory and run in a subprocess) and by the current ones. Writes results/i_r2/key_form_diff.tsv
(every value whose form changed) and key_form_diff.json (counts).
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import tempfile
from pathlib import Path

CODE = Path(__file__).resolve().parent
EVIDENCE = CODE.parent
REPO = EVIDENCE.parents[3]
REL = EVIDENCE.relative_to(REPO)
OUT = EVIDENCE / "results" / "i_r2"


def collect() -> list[tuple[str, str, str]]:
    vals: set[tuple[str, str, str]] = set()

    def walk(o, u):
        if isinstance(o, dict):
            if o.get("t") in ("formula", "set") and isinstance(o.get("latex"), str):
                vals.add((u, "latex", o["latex"]))
            if isinstance(o.get("symbol"), str):
                vals.add((u, "symbol", o["symbol"]))
            if isinstance(o.get("symbols"), dict):
                for k in o["symbols"]:
                    vals.add((u, "symbol", k))
            if o.get("op") in ("member", "cmp", "forall"):
                for k in ("x", "lhs", "rhs", "var", "set"):
                    if isinstance(o.get(k), str):
                        vals.add((u, "latex", o[k]))
            for k, v in o.items():
                if k == "param_values" and isinstance(v, dict):
                    for x in v.values():
                        if isinstance(x, str):
                            vals.add((u, "latex", x))
                walk(v, u)
        elif isinstance(o, list):
            for v in o:
                walk(v, u)

    r = EVIDENCE / "results"
    dirs = [r / "s0/reference", r / "s0/trace_stored", *sorted((r / "s0/stored").glob("*")),
            r / "s0r2/reference_v1", *sorted((r / "s0r2/stored").glob("*"))]
    for d in dirs:
        for f in sorted(d.glob("*.json")):
            b = json.loads(f.read_text())
            walk(b.get("batch", b), f.stem)
    return sorted(vals)


def emit(code_dir: Path) -> None:
    """Print {"unit\\tkind\\tvalue": form} using the instruments under ``code_dir``."""
    sys.path.insert(0, str(code_dir))
    from instruments.values import canonical_latex, canonical_symbol

    ren = json.loads((EVIDENCE / "results/s1/renditions.json").read_text())
    samples = [json.loads((EVIDENCE / "sample.json").read_text()),
               json.loads((EVIDENCE / "results/s0r2/sample.json").read_text())]
    for smp in samples:
        for d in {u.get("rendition_dir") for u in smp["units"].values()} - {None, "results/s1"}:
            ren.update(json.loads((EVIDENCE / d / "renditions.json").read_text()))
    page = {u: m["page"] for smp in samples for u, m in smp["units"].items()}
    out = {}
    for u, k, s in collect():
        macros = ren.get(page.get(u), {}).get("parse_detail", {}).get("macros", {})
        out[f"{u}\t{k}\t{s}"] = canonical_latex(s, macros) if k == "latex" else canonical_symbol(s, macros)
    json.dump(out, sys.stdout, ensure_ascii=False)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--before", default="35ea59a")
    ap.add_argument("--emit", type=Path, help=argparse.SUPPRESS)
    a = ap.parse_args()
    if a.emit:
        emit(a.emit)
        return 0
    with tempfile.TemporaryDirectory() as tmp:
        arch = subprocess.run(["git", "-C", str(REPO), "archive", a.before, f"{REL}/code/mathgrammar", f"{REL}/code/instruments"],
                              capture_output=True, check=True).stdout
        subprocess.run(["tar", "-x", "-C", tmp], input=arch, check=True)
        old_code = Path(tmp) / REL / "code"
        before = json.loads(subprocess.run([sys.executable, __file__, "--emit", str(old_code)], capture_output=True,
                                           text=True, check=True).stdout)
    after = json.loads(subprocess.run([sys.executable, __file__, "--emit", str(CODE)], capture_output=True,
                                      text=True, check=True).stdout)
    assert before.keys() == after.keys()
    moved = [(k, before[k], after[k]) for k in sorted(before) if before[k] != after[k]]
    OUT.mkdir(parents=True, exist_ok=True)
    with (OUT / "key_form_diff.tsv").open("w", encoding="utf-8") as fh:
        fh.write("unit\tkind\tvalue\tform_before\tform_after\n")
        for k, b, c in moved:
            fh.write(f"{k}\t{b}\t{c}\n")
    summary = {"before": a.before, "values": len(before), "moved": len(moved),
               "moved_values": sorted({k.split("\t")[2] for k, *_ in moved})}
    (OUT / "key_form_diff.json").write_text(json.dumps(summary, indent=1, ensure_ascii=False) + "\n")
    print(json.dumps(summary, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
