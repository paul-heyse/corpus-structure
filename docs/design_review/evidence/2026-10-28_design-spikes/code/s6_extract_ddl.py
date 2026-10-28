"""S6-A: extract D3's SQL blocks by script (never retyped) and build the applied copy with fixes.

    uv run python code/s6_extract_ddl.py            # from the evidence folder

Writes
- ``code/s6_ddl.sql``: every D3 ``sql`` block that holds DDL (CREATE/ALTER/DO), verbatim, in
  document order, each headed by its D3 line range and section;
- ``code/s6_queries_d3.sql``: the query blocks (D3 §5 BM25 query, §9 patterns), verbatim;
- ``code/s6_ddl_applied.sql``: ``s6_ddl.sql`` with the fixes of ``code/s6_ddl_fixes.py``
  applied, each marked in place by a ``-- S6 fix <id>`` comment;
- ``results/s6/ddl_fixes.md``: the fixes with their reasons, rendered from the same list.

A fix that does not match exactly once fails the script, so the copy cannot drift from D3 silently.
"""

from __future__ import annotations

import hashlib
import re
import sys
from pathlib import Path

CODE = Path(__file__).resolve().parent
EVIDENCE = CODE.parent
REPO = EVIDENCE.parents[3]
D3 = REPO / "docs" / "design" / "D3-database.md"
RESULTS = EVIDENCE / "results" / "s6"

sys.path.insert(0, str(CODE))
from s6_ddl_fixes import FIXES  # noqa: E402

DDL_RE = re.compile(r"^\s*(CREATE|ALTER|DO)\b", re.I | re.M)


def blocks(text: str) -> list[dict]:
    out, section, cur = [], "", None
    for i, line in enumerate(text.splitlines(), start=1):
        if cur is None:
            if line.startswith("## "):
                section = line[3:].strip()
            if line.strip() == "```sql":
                cur = {"start": i + 1, "section": section, "lines": []}
        elif line.strip() == "```":
            cur["end"] = i - 1
            cur["sql"] = "\n".join(cur.pop("lines")) + "\n"
            out.append(cur)
            cur = None
        else:
            cur["lines"].append(line)
    return out


def main() -> int:
    text = D3.read_text()
    d3_sha = hashlib.sha256(text.encode()).hexdigest()
    bs = blocks(text)
    ddl, queries = [], []
    for b in bs:
        head = f"-- D3 lines {b['start']}-{b['end']} ({b['section']})\n"
        (ddl if DDL_RE.search(b["sql"]) else queries).append(head + b["sql"])
    preamble = f"-- Extracted from docs/design/D3-database.md (sha256 {d3_sha}) by code/s6_extract_ddl.py; do not edit.\n\n"
    ddl_sql = preamble + "\n".join(ddl)
    (CODE / "s6_ddl.sql").write_text(ddl_sql)
    (CODE / "s6_queries_d3.sql").write_text(preamble + "\n".join(queries))

    applied = ddl_sql
    for f in FIXES:
        n = applied.count(f["old"])
        if n != 1:
            print(f"fix {f['id']}: expected one match, found {n}", file=sys.stderr)
            return 1
        applied = applied.replace(f["old"], f"-- S6 fix {f['id']}: {f['short']}\n" + f["new"])
    applied = applied.replace(preamble, preamble.replace("do not edit.", "with the S6 fixes of code/s6_ddl_fixes.py applied.") , 1)
    (CODE / "s6_ddl_applied.sql").write_text(applied)

    RESULTS.mkdir(parents=True, exist_ok=True)
    md = [
        "# S6 DDL fixes",
        "",
        f"Source: `docs/design/D3-database.md` (sha256 `{d3_sha[:16]}…`), {len(ddl)} DDL blocks and "
        f"{len(queries)} query blocks extracted by `code/s6_extract_ddl.py` into `code/s6_ddl.sql` and "
        "`code/s6_queries_d3.sql`. The applied copy is `code/s6_ddl_applied.sql`; D3 is not edited.",
        "",
    ]
    if not FIXES:
        md.append("No fixes: the extracted DDL applies as written.")
    for f in FIXES:
        md += [f"## {f['id']}: {f['short']}", "", f"- **Error or gap:** {f['error']}", f"- **Fix:** {f['fix']}",
               f"- **Reason:** {f['reason']}", f"- **Kind:** {f['kind']}", "", "```sql", "-- D3", f["old"].rstrip(), "-- copy", f["new"].rstrip(), "```", ""]
    (RESULTS / "ddl_fixes.md").write_text("\n".join(md) + "\n")
    print(f"{len(ddl)} DDL blocks, {len(queries)} query blocks, {len(FIXES)} fixes")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
