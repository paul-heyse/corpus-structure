"""Grammar coverage on the 78 first-pass pages, reported beside S5-A's (record `s5.coverage`).

Corpus-gated (ingest and math §5 P0-I-2a, §6). Every math span of the production renditions is read
under `any_value` with its rendition's effective macro table. Coverage is reported per page, not a
gate; S5's per-span reading is the thin fixture `data/s5_coverage.json`. The test fails only on what
is a defect at any coverage: a span set that differs from S5's (the inputs moved), an `internal`
failure (a crash after parsing), or a disagreement of the tree/token property (D1 §6.2).

Status changes against S5 are listed by cause:

- `timeout` on either side is timing: the one deadline now bounds the whole read, the ambiguity
  resolver's SymPy conversions included (S5 bounded the resolver apart, 1 s per reading and 4 s
  per value), so spans whose readings SymPy cannot finish evaluating (`\\int_0^\\infty h(t)\\,dt =
  \\infty`) end as `timeout` instead of `ambiguous`; long display spans near the 2 s limit may flip
  between runs;
- a non-`Expr` product (SymPy's deprecated path) is refused, so readings once merged through it
  stay `ambiguous`.
"""

from __future__ import annotations

import csv
import hashlib
import json
from collections import Counter
from typing import Any

import pytest

pytestmark = [
    pytest.mark.corpus,
    pytest.mark.filterwarnings("error::sympy.utilities.exceptions.SymPyDeprecationWarning"),
]
LETTER = {"ok": "o", "ambiguous": "a", "partial": "p", "failed": "f"}
STATUS = {v: k for k, v in LETTER.items()}


def test_coverage_beside_s5(env: Any, coverage_of: Any) -> None:
    with env.index.open(encoding="utf-8") as f:
        pages = [r["path"] for r in csv.DictReader(f, delimiter="\t") if r["first_pass"] == "yes"]
    s5 = json.loads((env.data / "s5_coverage.json").read_text(encoding="utf-8"))
    assert len(pages) == len(s5["pages"]) == 78
    got = coverage_of(pages)
    totals: Counter[str] = Counter()
    changes: list[tuple[str, str, str, str]] = []
    internal, disagreements = [], []
    heads = ["ok", "ambiguous", "partial", "failed"]
    print("\npage | spans | " + " | ".join(heads + [f"S5 {h}" for h in heads]))
    for page in sorted(pages):
        rows = got[page]
        expected = s5["pages"][page]
        bounds = json.dumps([[r.start, r.end] for r in rows])
        assert hashlib.sha256(bounds.encode()).hexdigest() == expected["bounds_sha256"], page
        mine = "".join(LETTER[r.status] for r in rows)
        counts, theirs = Counter(mine), Counter(expected["status"])
        totals.update(r.status for r in rows)
        print(
            f"{page} | {len(rows)} | "
            + " | ".join(str(counts[c]) for c in "oapf")
            + " | "
            + " | ".join(str(theirs[c]) for c in "oapf")
        )
        for i, (row, before) in enumerate(zip(rows, expected["status"], strict=True)):
            if LETTER[row.status] != before:
                was = STATUS[before] + (f" ({expected['failed'][str(i)]})" if before == "f" else "")
                now = row.status + (
                    f" ({row.category})" if row.category and row.status == "failed" else ""
                )
                changes.append((page, was, now, row.text[:100]))
            if row.category == "internal":
                internal.append((page, row.start, row.text[:100]))
            if row.agrees is False:
                disagreements.append((page, row.start, row.text[:100]))
    print(f"totals: {dict(totals)}; S5: {s5['extended']}")
    timing = [c for c in changes if "(timeout)" in c[1] or "(timeout)" in c[2]]
    print(f"status changes against S5: {len(changes)} ({len(timing)} with a timeout on one side)")
    for change in changes:
        print("  ", *change)
    assert internal == []
    assert disagreements == []
