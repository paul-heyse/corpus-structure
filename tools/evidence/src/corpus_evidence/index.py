"""Generated navigation: each folder README's records block and the evidence README's table."""

from __future__ import annotations

import re
from pathlib import Path

from jinja2 import Environment, PackageLoader, StrictUndefined

from .store import Folder, Store

START, END = "<!-- evidence-index:start -->", "<!-- evidence-index:end -->"
_ENV = Environment(
    loader=PackageLoader("corpus_evidence", "templates"),
    undefined=StrictUndefined,
    keep_trailing_newline=False,
    autoescape=False,
)
_ITEM = re.compile(r"[A-Z][A-Z0-9]*-[A-Z0-9]+(?:-[0-9]+)?")


def _row(rec) -> dict:
    d = rec.model_dump(mode="json")
    d["group_label"] = rec.group or "Other"
    d["sort_key"] = (rec.package or "~", rec.id)
    return d


def folder_block(folder: Folder) -> str:
    return _ENV.get_template("folder_index.md.j2").render(
        records=[_row(r) for r in folder.records.values()]
    )


def root_block(store: Store) -> str:
    rows = []
    for f in store.folders.values():
        recs = [r for r in f.records.values() if r.status == "current"]
        answers = sorted({a for r in recs for a in r.answers if _ITEM.fullmatch(a)})
        # records consumed by other records of the folder are internal; list outside consumers
        consumers = sorted({c for r in recs for c in r.consumed_by if c not in f.records})
        rows.append(
            {
                "name": f.name,
                "title": f.title(),
                "current": len(recs),
                "total": len(f.records),
                "answers": answers[:12] + ([f"+{len(answers) - 12}"] if len(answers) > 12 else []),
                "consumers": consumers,
            }
        )
    return _ENV.get_template("root_index.md.j2").render(folders=rows)


def splice(text: str, block: str, heading: str) -> str:
    """Replace the marked block, or append it under `heading` when the README has none."""
    body = f"{START}\n{block.strip()}\n{END}"
    if START in text and END in text:
        pre, rest = text.split(START, 1)
        _, post = rest.split(END, 1)
        return pre + body + post
    return text.rstrip() + f"\n\n{heading}\n\n{body}\n"


def plan(store: Store) -> dict[Path, str]:
    """README path → its content with current generated blocks."""
    out: dict[Path, str] = {}
    root_readme = store.root / "README.md"
    if root_readme.exists():
        out[root_readme] = splice(
            root_readme.read_text(encoding="utf-8"), root_block(store), "## Index"
        )
    for f in store.folders.values():
        readme = f.path / "README.md"
        if readme.exists() and f.records:
            out[readme] = splice(readme.read_text(encoding="utf-8"), folder_block(f), "## Records")
    return out


def write(store: Store) -> list[Path]:
    changed = []
    for path, text in plan(store).items():
        if path.read_text(encoding="utf-8") != text:
            path.write_text(text, encoding="utf-8")
            changed.append(path)
    return changed


def stale(store: Store) -> list[Path]:
    return [p for p, t in plan(store).items() if p.read_text(encoding="utf-8") != t]
