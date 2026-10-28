"""The V1/V2 canonicalization (S4 variants), importable without LinkML.

V1: ``{"t": "entity", "ref": r}`` becomes ``{"ref": r}``, and a dict-valued identity slot ``{"ref": r}``
becomes the local-ref string ``r``. V2: an entities[] item of type Statement becomes a statements[] item
anchored ``outside`` (kind theorem: every such item in the inputs names a result). Each rewrite is
reported, so every migrated batch is a recorded batch defect.
"""

from __future__ import annotations

import copy


def canonicalize(batch: dict) -> tuple[dict, list[str]]:
    b = copy.deepcopy(batch)
    notes: list[str] = []

    def walk(o, path):
        if isinstance(o, dict):
            for k, v in list(o.items()):
                if isinstance(v, dict) and v.get("t") == "entity" and set(v) == {"t", "ref"}:
                    o[k] = {"ref": v["ref"]}
                    notes.append(f"V1 {path}/{k}: {{t: entity, ref}} -> {{ref}}")
                else:
                    walk(v, f"{path}/{k}")
        elif isinstance(o, list):
            for i, v in enumerate(o):
                if isinstance(v, dict) and v.get("t") == "entity" and set(v) == {"t", "ref"}:
                    o[i] = {"ref": v["ref"]}
                    notes.append(f"V1 {path}/{i}: {{t: entity, ref}} -> {{ref}}")
                else:
                    walk(v, f"{path}/{i}")

    for i, c in enumerate(b.get("claims", [])):
        walk(c.get("qualifiers") or {}, f"claims/{i}/qualifiers")
    for i, e in enumerate(b.get("entities", [])):
        for k, v in list((e.get("identity") or {}).items()):
            if isinstance(v, dict) and "ref" in v:
                e["identity"][k] = v["ref"]
                notes.append(f"V1 entities/{i}/identity/{k}: {{ref}} -> local-ref string")
    keep = []
    for e in b.get("entities", []):
        if e.get("type") == "Statement":
            b.setdefault("statements", []).append({"local_ref": e["local_ref"], "kind": "theorem", "anchor": "outside"})
            notes.append(f"V2 entity {e['local_ref']} (Statement, {e.get('label')!r}) -> statements[] anchor outside, kind theorem")
        else:
            keep.append(e)
    b["entities"] = keep
    return b, notes
