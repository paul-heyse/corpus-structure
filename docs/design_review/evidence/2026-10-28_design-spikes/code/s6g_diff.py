"""S6-G: the corrected DDL as a unified diff against D3's blocks, for the report.

    uv run python code/s6g_diff.py

Diffs ``code/s6_ddl.sql`` (D3's blocks as extracted for S6-A) against ``code/s6_ddl_applied.sql``
into ``results/s6/ddl.diff`` (the extraction header excluded), and checks that the SQL blocks of the
current ``docs/design/D3-database.md`` are still the ones extracted, so the diff applies to D3 as
it stands. Prints the check; exits 1 if D3's SQL has moved on.
"""

from __future__ import annotations

import difflib
import re
import sys
from pathlib import Path

CODE = Path(__file__).resolve().parent
sys.path.insert(0, str(CODE))
from s6_extract_ddl import D3, DDL_RE, RESULTS, blocks  # noqa: E402


def body(sql: str) -> list[str]:
    return [ln for ln in sql.splitlines(keepends=True) if not ln.startswith("-- Extracted from") and not re.match(r"-- D3 lines \d+-\d+", ln)]


def main() -> int:
    d3 = body(CODE.joinpath("s6_ddl.sql").read_text())
    applied = body(CODE.joinpath("s6_ddl_applied.sql").read_text())
    diff = difflib.unified_diff(d3, applied, fromfile="D3 §3–§8 DDL (code/s6_ddl.sql)", tofile="S6 applied copy (code/s6_ddl_applied.sql)", n=2)
    RESULTS.mkdir(parents=True, exist_ok=True)
    (RESULTS / "ddl.diff").write_text("".join(diff))
    current = [b["sql"] for b in blocks(D3.read_text()) if DDL_RE.search(b["sql"])]
    extracted = [x.split("\n", 1)[1] for x in CODE.joinpath("s6_ddl.sql").read_text().split("-- D3 lines ")[1:]]
    same = [c.strip() for c in current] == [e.strip() for e in extracted]
    print("current D3 DDL blocks equal the extracted ones:", same)
    return 0 if same else 1


if __name__ == "__main__":
    raise SystemExit(main())
