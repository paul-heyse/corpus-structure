"""Q-1 probe: the hand-written part the generated shapes import (plan §3.3: behaviour stays in
hand-written functions over the generated types).

- Python aliases for LinkML types the generator maps by ci:py_type: they carry what LinkML cannot state
  on a string (min length) or a marker (CITATION on SentenceId). SentenceId, Offset, LocalRef and
  PrefixedName are the product's own aliases (read-only import).
- Validator hooks named by ci:validator: the same rules as the hand model validators in values.py and
  batch.py, written over the generated classes (they read fields, not product classes).
"""

from __future__ import annotations

import re
from typing import Annotated, Any, Literal

from pydantic import MISSING, BaseModel, Field

from corpus_structure.core.batch import LocalRef, PrefixedName  # noqa: F401  (re-exported for the module)
from corpus_structure.core.values import Offset, SentenceId  # noqa: F401
from corpus_structure.core.vocab import EntityScope, EvidenceRole, StatementRole  # noqa: F401

NonEmptyStr = Annotated[str, Field(min_length=1)]
AuthoredAnchor = Literal["unit", "outside"] | Annotated[tuple[SentenceId, ...], Field(min_length=1)]
StoredAnchor = Literal["outside"] | Annotated[tuple[str, ...], Field(min_length=1)]

_PREFIXED = re.compile(r"^[a-z][a-z0-9_]*:[A-Za-z_][A-Za-z0-9_]*$")
_BINDING_FIELDS: dict[str, frozenset[str]] = {
    "variable": frozenset({"entity"}), "family_param": frozenset({"entity"}),
    "param_of": frozenset({"claim", "param"}), "param_expr_of": frozenset({"claim", "param"}),
    "free": frozenset(), "constant": frozenset(), "unresolved": frozenset(),
}


def binding_fields(self):
    wanted = _BINDING_FIELDS[self.bind]
    present = {n for n in ("entity", "claim", "param") if getattr(self, n) is not MISSING}
    if present != wanted:
        need = ", ".join(sorted(wanted)) or "no other field"
        raise ValueError(f"a {self.bind} binding takes {need}; got {sorted(present) or 'none'}")
    return self


def extent_only_local(self):
    if self.scope is EntityScope.GLOBAL and self.extent is not MISSING:
        raise ValueError("only a local entity has an extent")
    return self


def schema_qualifiers_prefixed(self):
    for name in self.__pydantic_extra__ or {}:
        if not _PREFIXED.match(name):
            raise ValueError(f"stored qualifier {name!r} is not a prefixed name")
        if name.startswith("core:"):
            raise ValueError(f"{name!r} is not a core qualifier")
    return self


def _m11(value: Any, path: str = "$") -> list[str]:
    found: list[str] = []
    if isinstance(value, BaseModel):
        if getattr(type(value), "__ci_expression__", False):
            for name in ("sympy", "parse"):
                if getattr(value, name) is not MISSING:
                    found.append(f"{path}.{name}")
        for name in type(value).model_fields:
            found += _m11(getattr(value, name), f"{path}.{name}")
        for name, extra in (value.__pydantic_extra__ or {}).items():
            found += _m11(extra, f"{path}.{name}")
    elif isinstance(value, dict):
        for k, v in value.items():
            found += _m11(v, f"{path}.{k}")
    elif isinstance(value, tuple | list):
        for i, v in enumerate(value):
            found += _m11(v, f"{path}[{i}]")
    return found


def well_formed_batch(self):
    seen: dict[str, str] = {}
    for kind in ("entities", "statements", "claims", "unsupported"):
        for item in getattr(self, kind):
            if item.local_ref in seen:
                raise ValueError(f"local ref {item.local_ref!r} is used by {seen[item.local_ref]} and {kind}")
            seen[item.local_ref] = kind
    m11 = _m11(self)
    if m11:
        raise ValueError(f"sympy and parse are set by M11 only, never in a batch: {m11}")
    return self
