"""The page split (D7 §3.1, §4; D3 §7; evaluation §3.1, P0-E-1) and the pack's evaluation values.

The pack's values are its `eval/split.yaml` (D7 §3.1, D2 §2), read by `load_eval` into
`EvalConfig`: the split seed, the forced-dev pages with their reasons, the reserved pages of the
worked examples, the slices whose units are forced into a dev set, and the set sizes. Pages are
relative to the source profile's root. An absent file is the defaults.

`split_documents(conn, project_id, config, seed)` assigns every registered document of the project
once, in one transaction:

1. **reserved**: the worked examples' pages, in no split;
2. **forced dev**: the declared pages, each with its reason; a page both reserved and forced is
   refused;
3. **hash**: the rest, grouped by chapter (`kb.document.meta.chapter`, those without one forming a
   group), ordered by `sha256(source_uri + str(seed))` over the UTF-8 encoded URI as stored; within
   each group the documents at 0-based index mod 5 = 4 go to test and the rest to dev.

Existing rows never change. A document registered later is ordered among its chapter's unassigned
documents only, so it cannot move an assigned one; a document whose source URI already has an
assignment (new bytes at a known page) takes that page's split. A pack change that contradicts an
existing row (a page newly reserved or forced that sits elsewhere) is refused, listing each.
`assign` is the pure rule; `split_of` is the split lookup.
"""

from __future__ import annotations

import hashlib
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, replace
from pathlib import Path

import yaml
from pydantic import BaseModel, ConfigDict, Field, ValidationError

from corpus_structure.core.vocab import DocumentSplit

TEST_EVERY = 5


class SplitError(ValueError):
    """A split the pack's values or the existing rows refuse."""


class _Frozen(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


class SplitConfig(_Frozen):
    seed: int = 0
    forced_dev: dict[str, str] = Field(default_factory=dict)  # page -> reason
    reserved: dict[str, str] = Field(default_factory=dict)  # page -> the worked example


class GoldenConfig(_Frozen):
    forced_slices: tuple[str, ...] = ()  # slices whose units are forced into a dev set
    sizes: dict[str, int] = Field(default_factory=lambda: {"dev": 40, "test": 40})


class EvalConfig(_Frozen):
    split: SplitConfig = SplitConfig()
    golden: GoldenConfig = GoldenConfig()


SPLIT_FILE = Path("eval") / "split.yaml"


def load_eval(pack: Path) -> EvalConfig:
    """The pack's `eval/split.yaml` (module doc); an absent file is the defaults."""
    path = pack / SPLIT_FILE
    if not path.exists():
        return EvalConfig()
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    try:
        return EvalConfig.model_validate(data)
    except ValidationError as error:
        raise SplitError(f"{path}: {error}") from None


@dataclass(frozen=True)
class SplitDocument:
    id: int
    source_uri: str
    chapter: str | None


@dataclass(frozen=True)
class Assignment:
    document_id: int
    split: DocumentSplit
    reason: str
    seed: str | None


def _on(uri: str, page: str) -> bool:
    return uri == page or uri.endswith("/" + page)


def _order(uri: str, seed: str) -> str:
    return hashlib.sha256((uri + seed).encode("utf-8")).hexdigest()


def assign(
    documents: Sequence[SplitDocument],
    config: SplitConfig,
    existing: Mapping[int, Assignment],
    seed: int | None = None,
) -> list[Assignment]:
    """The new assignments of the unassigned documents (module doc); input order is irrelevant."""
    seed_text = str(config.seed if seed is None else seed)
    both = sorted(set(config.reserved) & set(config.forced_dev))
    if both:
        raise SplitError(f"pages both reserved and forced to dev: {both}")
    by_id = {d.id: d for d in documents}
    by_uri = {by_id[i].source_uri: a for i, a in sorted(existing.items()) if i in by_id}
    conflicts = []
    for doc_id, a in sorted(existing.items()):
        uri = by_id[doc_id].source_uri if doc_id in by_id else ""
        if any(_on(uri, p) for p in config.reserved) and a.split is not DocumentSplit.RESERVED:
            conflicts.append(f"{uri} is newly reserved but assigned {a.split}")
        if any(_on(uri, p) for p in config.forced_dev) and a.split is not DocumentSplit.DEV:
            conflicts.append(f"{uri} is newly forced to dev but assigned {a.split}")
    if conflicts:
        raise SplitError("the pack contradicts existing assignments: " + "; ".join(conflicts))
    out: list[Assignment] = []
    groups: dict[str, list[SplitDocument]] = {}
    for d in sorted(documents, key=lambda d: d.id):
        if d.id in existing:
            continue
        reserved = [r for p, r in config.reserved.items() if _on(d.source_uri, p)]
        forced = [r for p, r in config.forced_dev.items() if _on(d.source_uri, p)]
        if reserved:
            out.append(Assignment(d.id, DocumentSplit.RESERVED, f"reserved: {reserved[0]}", None))
        elif forced:
            out.append(Assignment(d.id, DocumentSplit.DEV, f"forced_dev: {forced[0]}", None))
        elif d.source_uri in by_uri:  # new bytes at an assigned page keep the page's split
            a = by_uri[d.source_uri]
            out.append(Assignment(d.id, a.split, a.reason, a.seed))
        else:
            groups.setdefault(d.chapter or "", []).append(d)
    for chapter in sorted(groups):
        ordered = sorted(groups[chapter], key=lambda d: (_order(d.source_uri, seed_text), d.id))
        seen: dict[str, Assignment] = {}
        for d in ordered:
            if d.source_uri in seen:  # two documents of one page take one split
                out.append(replace(seen[d.source_uri], document_id=d.id))
                continue
            i = len(seen)
            split = DocumentSplit.TEST if i % TEST_EVERY == TEST_EVERY - 1 else DocumentSplit.DEV
            seen[d.source_uri] = Assignment(d.id, split, "hash", seed_text)
            out.append(seen[d.source_uri])
    return sorted(out, key=lambda a: a.document_id)


def split_documents(conn, project_id, config=None, seed=None):
    """Persist immutable semantic split assignments via the restricted evaluator."""
    from .semantic import split_documents as persist

    return persist(conn, project_id, config, seed)
