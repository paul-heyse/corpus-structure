"""S0-R2: inputs for the D7 adjudicator session over passes SV and HV (guideline v1).

    UV_PROJECT_ENVIRONMENT=$REPO/build/spike-venv uv run python code/s0r2_adjudication_inputs.py

Needs the SV-against-HV comparison (S0_SAMPLE=results/s0r2/sample.json S0_COMPARE=results/s0r2/compare
code/s0d_compare.py results/s0r2/stored/pass_sv results/s0r2/stored/pass_hv sv_vs_hv). Writes
results/s0r2/inputs/adjudication_v1/: the annotators' inputs (guideline, reference, format, packets),
both passes' model-facing batches, and per unit a diff from the alignment: matched claims with the
fields that differ, claims only in one pass, unmatched entities.
"""

from __future__ import annotations

import json
import re
import shutil
from pathlib import Path

EVIDENCE = Path(__file__).resolve().parent.parent
R2 = EVIDENCE / "results" / "s0r2"
SRC = R2 / "inputs" / "packet_v1"
OUT = R2 / "inputs" / "adjudication_v1"
ALIGN = R2 / "compare" / "sv_vs_hv" / "alignment.txt"
PASSES = {"A": "pass_sv", "B": "pass_hv"}

INSTRUCTIONS = """# Instructions for the adjudication session

Two annotators (passes A and B) independently annotated the same units following the guideline.
You adjudicate: for each unit you produce one final batch and a record of every decision.

## Read

1. `guideline.md`, `reference.md` (keep it open), `format.md`.
2. For each unit: `units/<unit>.md` (the packet both annotators had), `pass_a/<unit>.json` and
   `pass_b/<unit>.json`, and `diffs/<unit>.md` (their alignment: matched claims with the fields that
   differ, claims only in A or only in B, unmatched entities).

## Do

For each unit ({UNITS}):

1. Decide every difference in `diffs/<unit>.md`, and any other you see, with one of: **keep A**,
   **keep B**, **keep both** (a faithful ambiguity, an `alternatives` group), **drop both**, **rewrite**
   (neither follows the guideline; write the correct item). Mark a decision `guideline_gap` when the
   guideline does not settle it. Where both passes break a guideline rule, rewrite.
2. Write the final batch to `{OUT}/<unit>.json` (start from the closer pass and edit it).
3. Write `{OUT}/decisions/<unit>.md`: a table with one row per decision: item, decision,
   `guideline_gap` yes/no, one-line reason citing the guideline section.
4. Validate: `{VALIDATE}`. Fix issues; fix rule warnings unless the rule does not apply (say why).

When all are done, write `{OUT}/opened_files.txt`: every file you opened, one per line.

## Do not read

Anything outside this input folder and your output folder: no design documents, no other results,
no code, no Git history, no directory listings outside these two folders.

## Report

Units completed, validation outcome, the number of decisions and of `guideline_gap` decisions, and the
three guideline points that most often left a difference undecided.
"""


def blocks(text: str) -> dict[str, str]:
    return {m.group(1): m.group(2) for m in re.finditer(r"# unit (\S+)\n(.*?)(?=\n# unit |\Z)", text, re.S)}


def diff(unit: str, blk: str) -> str:
    core = re.search(r"^core: (\[.*\])$", blk, re.M)
    pairs = eval(core.group(1)) if core else []  # noqa: S307 - our own instrument's output
    fails = {(a, b): f for a, b, f in re.findall(r"^  (\S+)~(\S+) full-tier failures \[([^\]]*)\]", blk, re.M)}
    a = json.loads((R2 / PASSES["A"] / f"{unit}.json").read_text())
    b = json.loads((R2 / PASSES["B"] / f"{unit}.json").read_text())
    ca, cb = {c["local_ref"]: c for c in a["claims"]}, {c["local_ref"]: c for c in b["claims"]}
    matched_a, matched_b = {x for x, _ in pairs}, {y for _, y in pairs}
    L = [f"# Unit {unit}: pass A versus pass B", "",
         "From the comparison instrument's alignment (D7 §5). The direction does not matter.", "",
         "## Matched claims (same subject, predicate and object)", "", "| A claim | B claim | Predicate | Fields that differ |",
         "|---|---|---|---|"]
    for x, y in pairs:
        f = fails.get((x, y), "").replace("'", "") or "none"
        L.append(f"| {x} | {y} | {ca.get(x, {}).get('predicate', '?')} | {f} |")
    L += ["", "## Claims only in A", ""]
    L += [f"- {r} ({c['predicate']})" for r, c in ca.items() if r not in matched_a] or ["none"]
    L += ["", "## Claims only in B", ""]
    L += [f"- {r} ({c['predicate']})" for r, c in cb.items() if r not in matched_b] or ["none"]
    ent = re.search(r"ref only: (\[.*?\])\s+pred only: (\[.*?\])", blk)
    L += ["", "## Entities", "", f"- only in A: {ent.group(1) if ent else '?'}; only in B: {ent.group(2) if ent else '?'}",
          f"- unsupported items: A {len(a.get('unsupported', []))}, B {len(b.get('unsupported', []))}", ""]
    return "\n".join(L)


def main() -> int:
    if OUT.exists():
        shutil.rmtree(OUT)
    (OUT / "diffs").mkdir(parents=True)
    for f in ("guideline.md", "reference.md", "format.md", "schema.yaml", "model.md"):
        shutil.copy(SRC / f, OUT / f)
    shutil.copytree(SRC / "units", OUT / "units")
    units = sorted(p.stem for p in (OUT / "units").glob("*.md"))
    for side, d in PASSES.items():
        shutil.copytree(R2 / d, OUT / f"pass_{side.lower()}", ignore=shutil.ignore_patterns("first", "notes", "*.txt"))
    bl = blocks(ALIGN.read_text())
    for u in units:
        (OUT / "diffs" / f"{u}.md").write_text(diff(u, bl[u]) if u in bl else f"# Unit {u}\n\nNot aligned.\n")
    o = "results/s0r2/adjudication_v1"
    (OUT / "instructions_adj.md").write_text(INSTRUCTIONS.format(
        UNITS=", ".join(units), OUT=o,
        VALIDATE=("cd /home/paul/corpus-structure/docs/design_review/evidence/2026-10-28_design-spikes && "
                  "S0_SAMPLE=results/s0r2/sample.json UV_PROJECT_ENVIRONMENT=/home/paul/corpus-structure/build/spike-venv "
                  f"uv run python code/s0_check.py {o} --rules")))
    print("wrote", OUT, len(units), "units")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
