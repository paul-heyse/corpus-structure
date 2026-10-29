"""The hand-written part the generated core shapes use (model and projections §3.3; probe Q-1).

`core/_model/shapes.py` is generated from the model (`schema/stage_b.py`); what it calls, inherits
or names by hand is here, and this module never imports it:

- the `ci:validator` hooks: the canonical-decimal check of a number value (a corrective message,
  where a bare pattern would only refuse), the prefixed names of a stored qualifier set's schema
  qualifiers, a batch's well-formedness (unique local refs, no M11 field) and a keyed candidate
  set's unique ids;
- the `ci:mixin` method classes: a batch's `local_refs`, a build diagnostic's `to_json`;
- the citation frame (`CitationFrame`, `FrameEntry`), which stays hand-written: a root model over
  a mapping, read like one (probe Q-1). The model's `FrameEntries` names it (`ci:py_type`).

The modules that re-export the generated classes (`values`, `batch`, `payloads`, `candidates`,
`parse_detail`) re-export these too.
"""

from __future__ import annotations

import re
from collections.abc import Iterator
from typing import Annotated, Any

from pydantic import MISSING, BaseModel, ConfigDict, Field, JsonValue, RootModel

from corpus_structure.core._model.types import PREFIXED_NAME, SENTENCE_ID, CoreModel
from corpus_structure.core.canonical import CANONICAL_DECIMAL, canonical_decimal
from corpus_structure.core.vocab import ClaimModality

_DECIMAL = re.compile(CANONICAL_DECIMAL)
_PREFIXED = re.compile(PREFIXED_NAME)
CORE_PREFIX = "core"
_ = ClaimModality  # the core qualifiers' prefix is the core module's (names.PREFIX)


# --- Validator hooks (`ci:validator`) ----------------------------------------------------------


def canonical_number(v: str) -> str:
    """A number value's `v` is its D1 §6.2 canonical decimal; a non-canonical spelling is refused
    with the canonical one."""
    if _DECIMAL.fullmatch(v):
        return v
    try:
        spelled = canonical_decimal(v)
    except ValueError:
        raise ValueError(f"{v!r} is not a decimal number") from None
    raise ValueError(f"{v!r} is not a canonical decimal; write {spelled!r}")


def prefixed_extras(qualifiers: BaseModel) -> None:
    """A stored qualifier set's schema qualifiers are named by prefixed name, never `core:`."""
    for name in qualifiers.__pydantic_extra__ or {}:
        if not _PREFIXED.match(name):
            raise ValueError(f"stored qualifier {name!r} is not a prefixed name")
        if name.startswith(f"{CORE_PREFIX}:"):
            raise ValueError(f"{name!r} is not a core qualifier")


def refuse_m11_fields(value: Any, path: str = "$") -> list[str]:
    """Paths of values that carry a field M11 sets in consolidation (`sympy`, `parse`: a
    generated class's `CONSOLIDATED`), which no batch may hold."""
    found: list[str] = []
    if isinstance(value, BaseModel):
        for name in getattr(type(value), "CONSOLIDATED", ()):
            if getattr(value, name) is not MISSING:
                found.append(f"{path}.{name}")
        for name in type(value).model_fields:
            found += refuse_m11_fields(getattr(value, name), f"{path}.{name}")
        for name, extra in (value.__pydantic_extra__ or {}).items():
            found += refuse_m11_fields(extra, f"{path}.{name}")
    elif isinstance(value, dict):
        for key, item in value.items():
            found += refuse_m11_fields(item, f"{path}.{key}")
    elif isinstance(value, tuple | list):
        for i, item in enumerate(value):
            found += refuse_m11_fields(item, f"{path}[{i}]")
    return found


def well_formed(batch: BatchMethods) -> None:
    """A batch's local refs are unique across its items, and it holds no M11 field."""
    seen: dict[str, str] = {}
    for kind, ref in batch.local_refs():
        if ref in seen:
            raise ValueError(f"local ref {ref!r} is used by {seen[ref]} and {kind}")
        seen[ref] = kind
    m11 = refuse_m11_fields(batch)
    if m11:
        raise ValueError(f"sympy and parse are set by M11 only, never in a batch: {m11}")


def well_formed_candidates(candidates: Any) -> None:
    """A keyed candidate set's renditions are sorted and without duplicates, and its item ids are
    unique."""
    if list(candidates.renditions) != sorted(set(candidates.renditions)):
        raise ValueError("renditions are sorted and without duplicates")
    seen: set[str] = set()
    for item in (*candidates.entities, *candidates.statements, *candidates.references,
                 *candidates.claims, *candidates.unsupported):  # fmt: skip
        if item.id in seen:
            raise ValueError(f"candidate id {item.id!r} is used twice")
        seen.add(item.id)


# --- Method classes (`ci:mixin`) ---------------------------------------------------------------


class BatchMethods:
    """A batch envelope's methods (both forms)."""

    def local_refs(self) -> Iterator[tuple[str, str]]:
        """Each item's (kind, local ref), in batch order."""
        for kind in ("entities", "statements", "claims", "unsupported"):
            for item in getattr(self, kind):
                yield kind, item.local_ref


class ParseDetailMethods:
    """A build's diagnostics' methods."""

    def to_json(self) -> dict[str, JsonValue]:
        assert isinstance(self, BaseModel)
        return self.model_dump(mode="json")


# --- The citation frame ------------------------------------------------------------------------


class FrameEntry(CoreModel):
    """One cited sentence: its locator (D1 §3.4) and its canonical text."""

    locator: str = Field(min_length=1)
    text: str


class CitationFrame(RootModel[dict[Annotated[str, Field(pattern=SENTENCE_ID)], FrameEntry]]):
    """Maps each cited sentence id (`sN`, or `cN` of the standing context) to locator and text."""

    model_config = ConfigDict(frozen=True, json_schema_extra={"additionalProperties": False})

    def __getitem__(self, sentence: str) -> FrameEntry:
        return self.root[sentence]

    def __contains__(self, sentence: object) -> bool:
        return sentence in self.root

    def keys(self) -> Iterator[str]:
        """Explicit sentence IDs; RootModel iteration retains Pydantic tuple semantics."""
        return iter(self.root)
