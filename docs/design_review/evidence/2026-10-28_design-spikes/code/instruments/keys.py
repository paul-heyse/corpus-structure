"""Claim and meaning keys of a stored batch (D1 §10.1, D5 §5.2; instruments §6).

``key = prefix + ":" + sha256(canonical_json(parts)).hexdigest()[:32]``. Parts (dict layout is
an instrument choice; D1 §10.1 names only the components):

- statement ``stm``: ``{"anchor": sorted segment keys}``;
- local entity ``ent``: ``{"type", "scope_segment", "symbol"}`` (normalized symbol), or
  ``"label"`` (normalized label) when the entity has no symbol;
- global entity ``ent``: ``{"type", "identity": {slot: key or normalized text}, "label"}``; the
  batch's label stands in for consolidation's canonical label;
- claim ``clm``: ``{"subject", "predicate" (prefixed), "object": {"key"} | {"value"},
  "qualifiers": {...}}`` with the identity qualifiers modality and polarity (defaults dropped),
  ``statement`` (statement key), canonical ``conditions`` (claim refs replaced by keys, in
  topological order of condition references) and the predicate's ``ci:identity_qualifiers``.

The meaning key drops ``statement`` and replaces condition claim refs by the referenced claims'
*meaning* keys, so it does not depend on statements through premises either. A condition
reference cycle drops the claims on it with a reason (D5 §5.2).
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from typing import Any

from .batch import as_formula, ref_of
from .conditions import canonical_condition, canonical_json, claim_refs
from .schema_lookup import SchemaLookup
from .values import canonical_symbol, canonical_value, text_norm


def make_key(prefix: str, parts: Any) -> str:
    return f"{prefix}:{hashlib.sha256(canonical_json(parts).encode('utf-8')).hexdigest()[:32]}"


@dataclass
class BatchKeys:
    entity: dict[str, str] = field(default_factory=dict)  # entities and statements
    entity_parts: dict[str, dict] = field(default_factory=dict)
    claim: dict[str, str] = field(default_factory=dict)
    meaning: dict[str, str] = field(default_factory=dict)
    claim_parts: dict[str, dict] = field(default_factory=dict)
    meaning_parts: dict[str, dict] = field(default_factory=dict)
    dropped: dict[str, str] = field(default_factory=dict)


def compute_keys(batch: dict, lookup: SchemaLookup | None = None, macros: dict | None = None) -> BatchKeys:
    from .validate import default_lookup

    lk = lookup or default_lookup()
    out = BatchKeys()
    for s in batch.get("statements", []):
        parts = {"anchor": sorted(s.get("anchor", []))}
        out.entity_parts[s["local_ref"]] = parts
        out.entity[s["local_ref"]] = make_key("stm", parts)
    ents = {e["local_ref"]: e for e in batch.get("entities", [])}
    visiting: set[str] = set()

    def ekey(r: str) -> str | None:
        if r in out.entity:
            return out.entity[r]
        e = ents.get(r)
        if e is None or r in visiting:
            return None
        visiting.add(r)
        t = lk.bare(e["type"])
        if e.get("scope") == "local":
            parts = {"type": t, "scope_segment": e.get("scope_segment")}
            if e.get("symbol"):
                parts["symbol"] = canonical_symbol(e["symbol"], macros)
            else:
                parts["label"] = text_norm(e.get("label", ""))
        else:
            ident = {}
            for slot, v in sorted((e.get("identity") or {}).items()):
                vr = ref_of(v)
                ident[slot] = ekey(vr) if (vr in ents or vr in out.entity) else text_norm(str(v))
            parts = {"type": t, "identity": ident, "label": text_norm(e.get("label", ""))}
        visiting.discard(r)
        out.entity_parts[r] = parts
        out.entity[r] = make_key("ent", parts)
        return out.entity[r]

    for r in ents:
        ekey(r)

    claims = {c["local_ref"]: c for c in batch.get("claims", [])}

    def cond_trees(c):
        for name, v in (c.get("qualifiers") or {}).items():
            q = lk.qualifier(name)
            if q and q[0] == "condition" and isinstance(v, dict):
                yield name, v

    deps = {r: {x for _, t in cond_trees(c) for x in claim_refs(t)} for r, c in claims.items()}
    # topological order (Kahn); remaining nodes are on or behind cycles
    order, done = [], set()
    pending = dict(deps)
    while True:
        ready = sorted(r for r, d in pending.items() if all(x in done or x not in claims for x in d))
        if not ready:
            break
        for r in ready:
            order.append(r)
            done.add(r)
            del pending[r]
    for r in pending:
        out.dropped[r] = "condition reference cycle (or depends on one)"

    for r in order:
        c = claims[r]
        rule = lk.predicate(c["predicate"])
        obj = c.get("object") or {}
        oref = ref_of(obj)
        o_part = {"key": out.entity.get(oref)} if oref is not None else {"value": canonical_value(obj, macros)}
        base_q: dict[str, Any] = {}
        mod = (c.get("qualifiers") or {}).get("modality", "asserted")
        pol = (c.get("qualifiers") or {}).get("polarity", "positive")
        if mod != "asserted":
            base_q["modality"] = mod
        if pol != "positive":
            base_q["polarity"] = pol
        q_claim, q_mean = dict(base_q), dict(base_q)
        for name, v in (c.get("qualifiers") or {}).items():
            q = lk.qualifier(name)
            if q is None:
                continue
            kind, rng = q
            identity = name == "conditions" or (rule is not None and lk.bare(name) in rule.identity_qualifiers)
            if not identity:
                continue
            if kind == "condition":
                q_claim[name] = canonical_condition(v, macros, claim_key=lambda x: out.claim.get(x, x), ref_key=lambda x: out.entity.get(x, x))
                q_mean[name] = canonical_condition(v, macros, claim_key=lambda x: out.meaning.get(x, x), ref_key=lambda x: out.entity.get(x, x))
            elif kind == "map":
                vk = lk.map_value_kind(rng)
                m = {k: (canonical_value(as_formula(x, vk), macros) if vk in ("formula", "set") else text_norm(str(x))) for k, x in v.items()}
                q_claim[name] = q_mean[name] = m
            elif kind == "entity":
                q_claim[name] = q_mean[name] = {"key": out.entity.get(ref_of(v))}
            else:
                q_claim[name] = q_mean[name] = canonical_value(as_formula(v, kind) if kind in ("formula", "set") else v, macros)
        if c.get("statement"):
            q_claim["statement"] = out.entity.get(c["statement"])
        pred = rule.prefixed if rule else c["predicate"]
        subj = out.entity.get(c.get("subject"))
        cp = {"subject": subj, "predicate": pred, "object": o_part, "qualifiers": q_claim}
        mp = {"subject": subj, "predicate": pred, "object": o_part, "qualifiers": q_mean}
        out.claim_parts[r], out.meaning_parts[r] = cp, mp
        out.claim[r] = make_key("clm", cp)
        out.meaning[r] = make_key("clm", mp)
    return out


def _entity_causes(pa: dict | None, pb: dict | None) -> list[str]:
    if pa is None or pb is None:
        return ["unkeyed_entity"]
    causes = [k for k in sorted(set(pa) | set(pb)) if pa.get(k) != pb.get(k)]
    return causes or ["entity_key"]


def mismatch_causes(ka: BatchKeys, ra: str, kb: BatchKeys, rb: str, *, meaning: bool = False,
                    entity_map: dict[str, str] | None = None) -> list[str]:
    """Why the claim (or meaning) keys of an aligned pair differ; [] when they coincide."""
    pa = (ka.meaning_parts if meaning else ka.claim_parts).get(ra)
    pb = (kb.meaning_parts if meaning else kb.claim_parts).get(rb)
    if pa is None or pb is None:
        return ["unkeyed_claim"]
    if pa == pb:
        return []
    causes: list[str] = []
    rev = {v: k for k, v in ka.entity.items()}
    revb = {v: k for k, v in kb.entity.items()}

    def ent(ka_key, kb_key, where):
        a, b = rev.get(ka_key), revb.get(kb_key)
        for c in _entity_causes(ka.entity_parts.get(a), kb.entity_parts.get(b)):
            causes.append(f"{where}.{c}")

    if pa["subject"] != pb["subject"]:
        ent(pa["subject"], pb["subject"], "subject")
    if pa["predicate"] != pb["predicate"]:
        causes.append("predicate")
    if pa["object"] != pb["object"]:
        if "key" in pa["object"] and "key" in pb["object"]:
            ent(pa["object"]["key"], pb["object"]["key"], "object")
        elif "value" in pa["object"] and "value" in pb["object"]:
            t = pa["object"]["value"].get("t") if isinstance(pa["object"]["value"], dict) else None
            causes.append("object.canonical_latex" if t in ("formula", "set") else "object.value")
        else:
            causes.append("object.kind")
    qa, qb = pa["qualifiers"], pb["qualifiers"]
    for name in sorted(set(qa) | set(qb)):
        if qa.get(name) == qb.get(name):
            continue
        if name == "conditions":
            causes.append("conditions")
        elif name in ("modality", "polarity", "statement"):
            causes.append(name)
        elif isinstance(qa.get(name), dict) and isinstance(qb.get(name), dict) and set(qa[name]) == set(qb[name]) and all(isinstance(x, dict) and x.get("t") in ("formula", "set") for x in qa[name].values()):
            causes.append(f"{name}.canonical_latex")
        elif isinstance(qa.get(name), dict) and isinstance(qb.get(name), dict) and set(qa[name]) != set(qb[name]):
            causes.append(f"{name}.keys")
        else:
            causes.append(name)
    return causes or ["unknown"]
