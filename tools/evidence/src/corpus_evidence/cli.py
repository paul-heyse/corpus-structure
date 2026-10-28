"""`just evidence <command>`: check, finalize, index, catalog, render, schema.

Without a command: index, catalog, then check."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from . import catalog, index, report, store
from .model import json_schema

ROOT = Path("docs/design_review/evidence")
CATALOG = Path("build/evidence.duckdb")
SCHEMA_OUT = Path("tools/evidence/record.schema.json")


def _check(st: store.Store) -> int:
    issues = store.check(st)
    stale = index.stale(st)
    for i in issues:
        print(i)
    for p in stale:
        print(f"error: {p}: generated index is out of date (run `just evidence index`)")
    errors = sum(i.severity == "error" for i in issues) + len(stale)
    n = len(st.all_records())
    print(
        f"evidence: {n} records in {len(st.folders)} folders; {errors} errors, "
        f"{sum(i.severity == 'warning' for i in issues)} warnings"
    )
    return 1 if errors else 0


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="evidence", description=__doc__)
    ap.add_argument(
        "--root", type=Path, default=ROOT, help="the evidence root (default: %(default)s)"
    )
    ap.add_argument("--catalog", type=Path, default=CATALOG)
    sub = ap.add_subparsers(dest="cmd")
    sub.add_parser("check", help="validate records, hashes, references and generated indexes")
    fin = sub.add_parser("finalize", help="fill a record's file hashes and date")
    fin.add_argument("folder")
    fin.add_argument("ids", nargs="+")
    sub.add_parser("index", help="regenerate the README index blocks")
    sub.add_parser("catalog", help="rebuild the DuckDB catalog")
    ren = sub.add_parser("render", help="render a report template from the catalog")
    ren.add_argument("template", type=Path)
    ren.add_argument("-o", "--out", type=Path)
    sub.add_parser("schema", help="write the record JSON Schema")
    a = ap.parse_args(argv)

    st = store.load(a.root)
    if a.cmd == "check":
        return _check(st)
    if a.cmd == "finalize":
        folder = st.folders.get(a.folder)
        if folder is None:
            print(f"no evidence folder {a.folder}", file=sys.stderr)
            return 2
        for rid in a.ids:
            store.finalize(folder, rid)
            print(f"finalized {a.folder}/{rid}")
        return 0
    if a.cmd == "index":
        for p in index.write(st):
            print(f"updated {p}")
        return 0
    if a.cmd == "catalog":
        print(f"built {catalog.build(st, a.catalog)}")
        return 0
    if a.cmd == "render":
        out = a.out or a.template.with_name(a.template.name.removesuffix(".j2"))
        print(f"rendered {report.render(a.template, a.catalog, out)}")
        return 0
    if a.cmd == "schema":
        SCHEMA_OUT.write_text(json.dumps(json_schema(), indent=2) + "\n", encoding="utf-8")
        print(f"wrote {SCHEMA_OUT}")
        return 0
    # build: index, catalog, then check
    for p in index.write(st):
        print(f"updated {p}")
    st = store.load(a.root)
    catalog.build(st, a.catalog)
    print(f"built {a.catalog}")
    return _check(st)


if __name__ == "__main__":
    sys.exit(main())
