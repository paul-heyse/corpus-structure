"""The entity-type side-table check and the V1/V2 canonicalization (D2 §7.3).

JSON Schema cannot follow local references, so subject, object and qualifier classes, binding
targets, condition references and entity scope are checked here against the pack (a few dozen lines,
reading only the schema facts). ``canonicalize`` rewrites the two non-canonical shapes S4 chose away
(V1: ``{"t": "entity", "ref": r}`` and a dict-valued identity slot become ``{"ref": r}`` and ``r``;
V2: an entities[] item of type Statement becomes a statements[] item anchored ``outside``) and
reports each rewrite, so every migrated batch is a recorded batch defect.
"""

from __future__ import annotations

from .canonical import canonicalize  # noqa: F401  (re-exported)
from .pack import Pack


def _nodes(tree):
    if isinstance(tree, dict):
        yield tree
        for a in tree.get("args") or []:
            if isinstance(a, dict) and "op" in a:
                yield from _nodes(a)
        for k in ("arg", "body"):
            if isinstance(tree.get(k), dict):
                yield from _nodes(tree[k])


def _formulas(o):
    if isinstance(o, dict):
        if o.get("t") in ("formula", "set"):
            yield o
        for v in o.values():
            yield from _formulas(v)
    elif isinstance(o, list):
        for v in o:
            yield from _formulas(v)


def side_table_check(batch: dict, pack: Pack, form: str) -> list[str]:
    """Issues as ``code: message`` strings; the batch has already passed the compiled models."""
    out: list[str] = []
    kind: dict[str, str] = {}
    cls: dict[str, str] = {}
    scope: dict[str, str] = {}
    for sec, k in (("entities", "entity"), ("statements", "statement"), ("claims", "claim"), ("unsupported", "unsupported")):
        for it in batch.get(sec, []):
            r = it["local_ref"]
            if r in kind:
                out.append(f"duplicate_local_ref: {r}")
            kind[r] = k
            if sec == "entities":
                cls[r], scope[r] = it["type"], it["scope"]
            elif sec == "statements":
                cls[r], scope[r] = "Statement", "local"
    claims = {c["local_ref"]: c for c in batch.get("claims", [])}

    def need(r, target_cls, what):
        if r not in kind:
            out.append(f"unresolved_ref: {what} {r!r}")
        elif kind[r] not in ("entity", "statement"):
            out.append(f"wrong_ref_kind: {what} {r!r} is a {kind[r]}")
        elif target_cls and not pack.is_a(cls[r], target_cls):
            out.append(f"class_mismatch: {what} {r!r} is a {cls[r]}, expected {target_cls}")

    for e in batch.get("entities", []):
        t, r = e["type"], e["local_ref"]
        if pack.scope(t) != e["scope"]:
            out.append(f"scope_disagrees_with_class: {r} is {e['scope']}, {t} is {pack.scope(t)}")
        if e["scope"] == "local":
            if form == "model" and "extent" not in e:
                out.append(f"INV-05: local entity {r} without extent")
            if form == "stored" and not e.get("scope_segment"):
                out.append(f"INV-05: local entity {r} without scope_segment")
        elif "extent" in e or e.get("scope_segment"):
            out.append(f"INV-05: global entity {r} with an extent")
        keys = pack.identity_keys(t)
        if set(e.get("identity") or {}) != set(keys):
            out.append(f"identity_keys: {r} has {sorted(e.get('identity') or {})}, {t} needs {list(keys)}")
        for k, v in (e.get("identity") or {}).items():
            rng = pack.sv.induced_slot(k, t).range if k in keys else None
            if rng and rng in pack.sv.all_classes():
                need(v, rng, f"{r}.identity.{k}")
    for s in batch.get("statements", []):
        pass  # kind and anchor are typed by the compiled models
    for c in batch.get("claims", []):
        p, r = pack.predicates[c["predicate"]], c["local_ref"]
        need(c["subject"], p.domain, f"{r}.subject")
        if p.object_kind == "entity":
            need(c["object"]["ref"], p.range, f"{r}.object")
        if "statement" in c and kind.get(c["statement"]) != "statement":
            out.append(f"wrong_ref_kind: {r}.statement {c['statement']!r}")
        q = c.get("qualifiers") or {}
        for qn, qv in q.items():
            qi = pack.qualifiers[qn]
            if qi.object_kind == "entity":
                need(qv["ref"], qi.range, f"{r}.qualifiers.{qn}")
        for tree_q in ("conditions", "param_constraints"):
            for n in _nodes(q.get(tree_q)):
                if n["op"] == "claim" and kind.get(n["ref"]) != "claim":
                    out.append(f"INV-08: {r} condition node names {n['ref']!r}, not a claim of the batch")
                if n["op"] == "pred":
                    cp = pack.pv_annotations("ConditionPredicate").get(n["name"])
                    if cp is None:
                        out.append(f"unknown_condition_predicate: {r} {n['name']!r}")
                        continue
                    ar = str(cp.get("ci:arity", ""))
                    if (ar == "2+" and len(n["args"]) < 2) or (ar.isdigit() and len(n["args"]) != int(ar)):
                        out.append(f"condition_arity: {r} {n['name']} has {len(n['args'])} args")
                    for a in n["args"]:
                        if "ref" in a:
                            need(a["ref"], cp.get("ci:args"), f"{r}.{n['name']} argument")
        for f in _formulas(c):
            for sym, b in (f.get("symbols") or {}).items():
                if b["bind"] == "variable":
                    if kind.get(b["entity"]) != "entity" or scope.get(b["entity"]) != "local":
                        out.append(f"binding_target: {r} {sym} variable names {b['entity']!r}, not a local entity")
                elif b["bind"] == "family_param":
                    pc = [c_ for c_, a in pack.entity_classes.items() if a.get("ci:parameter_class")]
                    if kind.get(b["entity"]) != "entity" or not any(pack.is_a(cls[b["entity"]], x) for x in pc):
                        out.append(f"binding_target: {r} {sym} family_param names {b['entity']!r}, not a parameter entity")
                elif b["bind"] in ("param_of", "param_expr_of"):
                    tgt = claims.get(b["claim"])
                    pm = pack.predicates[tgt["predicate"]].param_map if tgt else None
                    if tgt is None or pm is None or b["param"] not in ((tgt.get("qualifiers") or {}).get(pm) or {}):
                        out.append(f"binding_target: {r} {sym} {b['bind']} names {b['claim']!r}/{b['param']!r}, no such map entry")
        if not any(ev["role"] == "primary" for ev in c["evidence"]):
            out.append(f"INV-01: {r} without primary evidence")
    referenced = {n["ref"] for c in batch.get("claims", []) for n in _nodes((c.get("qualifiers") or {}).get("conditions")) if n["op"] == "claim"}
    for c in batch.get("claims", []):
        q = c.get("qualifiers") or {}
        if q.get("modality") == "supposed" and c["local_ref"] not in referenced and "scope" not in q:
            out.append(f"INV-06: supposed {c['local_ref']} neither referenced nor scoped")
    for a in batch.get("alternatives", []):
        for r in a["refs"]:
            if kind.get(r) != "claim":
                out.append(f"unresolved_ref: alternative member {r!r}")
    return out
