"""T2: the stored batch -> keyed candidate set adapter (P0-S-2; schema and rules §3.6).

`candidates_from_batch(stored, compiled)` implements foundations' T2 declaration
(`core/translations.py`): every item is carried, and nothing is silent.
- Entities, statements, claims (with `establishment`, `derived_from` and `rule`), alternatives,
  unsupported items and the rendition reference are carried over.
- An `outside` item becomes an `ExternalReference` node (`references`), `AWAITING` its resolution.
- Ids are the local refs and keys are `UNKEYED`; qualifier defaults come from the core models.
- Math delimiters are normalized: one outer `$…$`, `$$…$$`, `\\(…\\)` or `\\[…\\]` pair of a formula
  or set value is removed, so the spellings are equivalent (D4 §4.3 step 4); the LaTeX is
  otherwise kept as given.

The batch checks (`validate.batch`) have already refused wrong-kind and unresolved references, so
every reference of the candidate set is resolved or names an `ExternalReference`.
"""

from __future__ import annotations

import typing
from typing import Any

from pydantic import BaseModel

from corpus_structure.core.batch import StoredBatch, StoredOutside
from corpus_structure.core.candidates import KeyedCandidateSet

if typing.TYPE_CHECKING:
    from corpus_structure.schema.compile import CompiledSchema

DELIMITERS = (("$$", "$$"), ("\\[", "\\]"), ("\\(", "\\)"), ("$", "$"))


def normalize_delimiters(latex: str) -> str:
    """The LaTeX without one outer math delimiter pair (and the whitespace around it)."""
    text = latex.strip()
    for open_, close in DELIMITERS:
        if len(text) > len(open_) + len(close) and text.startswith(open_) and text.endswith(close):
            inner = text[len(open_) : -len(close)]
            if open_ == "$" and "$" in inner:
                continue  # `$a$ and $b$` is two formulas, not one delimited one
            return inner.strip()
    return latex


def _normalized(node: Any) -> Any:
    if isinstance(node, dict):
        out = {k: _normalized(v) for k, v in node.items()}
        if out.get("t") in ("formula", "set") and isinstance(out.get("latex"), str):
            out["latex"] = normalize_delimiters(out["latex"])
        return out
    if isinstance(node, list):
        return [_normalized(v) for v in node]
    return node


def _dump(item: BaseModel) -> dict[str, Any]:
    return item.model_dump(mode="json", by_alias=True)


def candidates_from_batch(stored: StoredBatch, compiled: CompiledSchema) -> KeyedCandidateSet:
    """The keyed candidate set of a stored batch's accepted items (module doc). `stored` is a
    stored batch of the compiled version (its stored model, or the core `StoredBatch`)."""
    del compiled  # the stored batch is already in the version's names; kept for the contract
    statements, references = [], []
    for st in stored.statements:
        d = _dump(st)
        if isinstance(st, StoredOutside):
            references.append({"id": d["local_ref"], "descriptor": d["descriptor"]})
        else:
            statements.append({"id": d["local_ref"], "kind": d["kind"], "anchor": d["anchor"]})
    entities = []
    for e in stored.entities:
        d = _dump(e)
        entities.append({"id": d.pop("local_ref"), **d})
    claims = []
    for c in stored.claims:
        d = _normalized(_dump(c))
        claims.append({"id": d.pop("local_ref"), **d})
    unsupported = []
    for u in stored.unsupported:
        d = _dump(u)
        unsupported.append({"id": d.pop("local_ref"), **d})
    return KeyedCandidateSet.model_validate(
        {
            "renditions": [stored.rendition],
            "entities": entities,
            "statements": statements,
            "references": references,
            "claims": claims,
            "alternatives": [_dump(a) for a in stored.alternatives],
            "unsupported": unsupported,
        }
    )
