"""Record citations in the design and the decision records, resolved against the store.

Design claims cite the records they rest on in three forms, all recognised:
- a link to the record file: `[s6.queue](../…/2026-10-28_design-spikes/records/s6.queue.json)`;
- a backticked id: `` `s4.rules` `` (also `` `s4.rules.json` ``);
- after the word "record" or "records", a list of ids, bare or backticked:
  "records s0r2.inputs, s0r2.scores", "records `s4.pack-lint`, `s4.batch-validation`".
A token needs a record id's shape (a dot after the prefix) and no file extension. A listed token
is a citation by its context; a backticked one only when its prefix (the part before the first
dot) is one a known record uses (`s0r2`, `p0q`, …), so code such as `self.con` is not taken for an
id. A citation of a superseded record or of an id no record has is a warning: the label it
supports needs a current record.
"""

from __future__ import annotations

import re
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path

from .model import Record
from .store import Folder, Issue, Store

# The documents whose claims cite records, relative to the docs root.
CITING = ("design/**/*.md", "adr/*.md")

_ID = r"[a-z0-9][a-z0-9\-]*\.[a-z0-9][a-z0-9.\-]*[a-z0-9]"
# An id-shaped token in prose, not part of a longer name (`ops.run.reference_run_id` is no id).
_WORD = rf"(?<![\w.\-]){_ID}(?![\w\-]|\.[a-z0-9])"
_LINK = re.compile(
    rf"(?:(?P<folder>[0-9]{{4}}-[0-9]{{2}}-[0-9]{{2}}_[a-z0-9\-]+)/)?records/(?P<id>{_ID})\.json"
)
_TICK = re.compile(rf"`(?P<id>{_ID})`")
_ITEM = rf"`?{_WORD}`?"
_LIST = re.compile(rf"\b[Rr]ecords?\s+\(?(?P<ids>{_ITEM}(?:(?:,\s*|,?\s+and\s+){_ITEM})*)")
_LISTED = re.compile(rf"`?(?P<id>{_WORD})`?")
# A trailing `.json` or a code or data file extension is not part of an id.
_FILE_EXT = re.compile(r"\.(?:py|sql|tsv|csv|yaml|yml|toml|txt|md|j2|rs|html|parquet)$")


@dataclass(frozen=True)
class Citation:
    path: Path
    line: int
    rid: str
    folder: str | None = None

    def where(self, docs: Path) -> str:
        try:
            rel = self.path.relative_to(docs.parent)
        except ValueError:
            rel = self.path
        return f"{rel}:{self.line}"


def _prefixes(store: Store) -> set[str]:
    return {r.id.split(".", 1)[0] for _, r in store.all_records()}


def _clean(token: str, prefixes: set[str], listed: bool) -> str | None:
    if token.endswith(".json"):
        token = token.removesuffix(".json")
    elif _FILE_EXT.search(token):
        return None
    return token if listed or token.split(".", 1)[0] in prefixes else None


def find(text: str, path: Path, prefixes: set[str]) -> list[Citation]:
    """Every record citation in one document, one per (line, id)."""
    out: dict[tuple[int, str], Citation] = {}
    for n, line in enumerate(text.splitlines(), start=1):
        for m in _LINK.finditer(line):
            out.setdefault((n, m["id"]), Citation(path, n, m["id"], m["folder"]))
        # a listed id is a citation by context; a backticked one by its known prefix
        tokens = [(x["id"], True) for m in _LIST.finditer(line) for x in _LISTED.finditer(m["ids"])]
        tokens += [(m["id"], False) for m in _TICK.finditer(line)]
        for tok, listed in tokens:
            rid = _clean(tok, prefixes, listed)
            if rid:
                out.setdefault((n, rid), Citation(path, n, rid))
    return list(out.values())


def documents(docs: Path) -> Iterable[Path]:
    for pattern in CITING:
        yield from sorted(docs.glob(pattern))


def _lookup(store: Store, c: Citation) -> list[tuple[Folder, Record]]:
    folders = [store.folders[c.folder]] if c.folder in store.folders else store.folders.values()
    return [(f, f.records[c.rid]) for f in folders if c.rid in f.records]


def collect(store: Store, docs: Path) -> list[Citation]:
    prefixes = _prefixes(store)
    return [c for p in documents(docs) for c in find(p.read_text(encoding="utf-8"), p, prefixes)]


def check(store: Store, docs: Path) -> list[Issue]:
    """Warnings for citations of superseded or unknown records in `docs`."""
    issues = []
    for c in collect(store, docs):
        hits = _lookup(store, c)
        if not hits:
            issues.append(Issue(c.where(docs), f"cites unknown record {c.rid}", "warning"))
            continue
        for folder, rec in hits:
            if rec.status == "superseded":
                issues.append(
                    Issue(
                        c.where(docs),
                        f"cites superseded record {c.rid} ({folder.name}); "
                        f"current: {rec.superseded_by}",
                        "warning",
                    )
                )
    return issues
