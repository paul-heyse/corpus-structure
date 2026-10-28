"""I-R2: migrate the root's manual value decisions to the token-form keys.

    UV_PROJECT_ENVIRONMENT=$REPO/build/spike-venv uv run python code/i_r2_migrate_manual.py

``results/s0/manual_equivalence.tsv`` holds the root's tier-4 decisions keyed by the canonical
forms of the two values. I-R2 changes those forms only for text-mode whitespace
(``results/i_r2/key_form_diff.tsv``), so a decision written under the old form no longer finds its
pair (ADR-0012's orphaned-judgment case). Each key that appears as a ``form_before`` of a formula
value in the diff is rewritten to its ``form_after``; nothing else changes (decision, reason, order).
Idempotent. Prints every rewritten key; the diff table must map each old form to one new form.
"""

from __future__ import annotations

import csv
import sys
from pathlib import Path

EVIDENCE = Path(__file__).resolve().parent.parent
MANUAL = EVIDENCE / "results" / "s0" / "manual_equivalence.tsv"
DIFF = EVIDENCE / "results" / "i_r2" / "key_form_diff.tsv"


def main() -> int:
    mapping: dict[str, str] = {}
    with DIFF.open(encoding="utf-8") as fh:
        for r in csv.DictReader(fh, delimiter="\t", quoting=csv.QUOTE_NONE):
            if r["kind"] != "latex":
                continue
            old, new = r["form_before"], r["form_after"]
            if mapping.setdefault(old, new) != new:
                raise SystemExit(f"{old!r} maps to two token forms: {mapping[old]!r}, {new!r}")
    lines = MANUAL.read_text(encoding="utf-8").splitlines()
    out = [lines[0]]
    for line in lines[1:]:
        parts = line.split("\t")
        if parts and parts[0] in ("formula", "set"):
            for i in (1, 2):
                if parts[i] in mapping:
                    print(f"{parts[i]!r} -> {mapping[parts[i]]!r}")
                    parts[i] = mapping[parts[i]]
        out.append("\t".join(parts))
    MANUAL.write_text("\n".join(out) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
