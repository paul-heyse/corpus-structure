"""The schema-table compiler (D2 §7.1; D3 §3): rows for meta.schema_class, schema_slot, schema_enum
and schema_rule, in D3's column names, without schema_version_id (the loader adds it).

Slot rows: predicates and qualifiers (ci:role), identity slots (in a class's unique_keys), and fields:
class slots (label, kind, symbol, t) by name, and class-local attributes of value classes as
``<prefix>:<Class>.<attribute>``, because D3's key (schema_version_id, name) cannot hold two
attributes of the same name in different classes (``v`` of TextValue and NumberValue).
"""

from __future__ import annotations

from .pack import Pack, annotations


def _native_class(c) -> dict:
    out = {}
    if c.title:
        out["title"] = str(c.title)
    if c.examples:
        out["examples"] = [str(e.value) for e in c.examples]
    if c.mixins:
        out["mixins"] = list(c.mixins)
    if c.abstract:
        out["abstract"] = True
    if c.mixin:
        out["mixin"] = True
    return out


def schema_tables(pack: Pack) -> dict:
    sv = pack.sv
    classes, slots, enums, rules = [], [], [], []
    identity = {s for c in sv.all_classes() for s in pack.identity_keys(c)}
    for n in sorted(sv.all_classes()):
        c = sv.get_class(n)
        a = {k: v for k, v in annotations(c).items()}
        a.update(_native_class(c))
        classes.append({
            "name": sv.get_uri(c, expand=False),
            "parent": sv.get_uri(sv.get_class(c.is_a), expand=False) if c.is_a else None,
            "kind": pack.class_kind(n),
            "scope": pack.scope(n),
            "identity_keys": list(pack.identity_keys(n)),
            "description": " ".join(str(c.description or "").split()) or None,
            "annotations": dict(sorted(a.items())),
        })
    for n in sorted(sv.all_slots()):
        s = sv.get_slot(n)
        a = annotations(s)
        role = a.get("ci:role") or ("identity" if n in identity else "field")
        ind = sv.induced_slot(n)
        if role == "predicate":
            i = pack.predicates[n]
            kind, quals, iq, subsets = i.object_kind, [pack.prefixed(q) for q in i.qualifiers], [pack.prefixed(q) for q in i.identity_qualifiers], list(i.subsets)
        elif role == "qualifier":
            kind, quals, iq, subsets = pack.qualifiers[n].object_kind, [], [], list(s.in_subset or [])
        else:
            kind, quals, iq, subsets = pack.object_kind(ind.range or "string")[0], [], [], list(s.in_subset or [])
        extra = {k: v for k, v in a.items() if k not in ("ci:role", "ci:qualifiers", "ci:identity_qualifiers", "ci:extract")}
        if s.symmetric:
            extra["symmetric"] = True
        if s.transitive:
            extra["transitive"] = True
        if s.ifabsent:
            extra["ifabsent"] = str(s.ifabsent)
        slots.append({
            "name": pack.prefixed(n),
            "role": role,
            "domain_class": ind.domain,
            "range": ind.range,
            "object_kind": kind,
            "multivalued": bool(ind.multivalued),
            "qualifiers": quals,
            "identity_qualifiers": iq,
            "subsets": subsets,
            "extract": a.get("ci:extract"),
            "description": " ".join(str(s.description or "").split()) or None,
            "annotations": dict(sorted(extra.items())),
        })
    # class-local attributes (fields of value classes and entries)
    for n in sorted(sv.all_classes()):
        c = sv.get_class(n)
        prefix = sv.get_uri(c, expand=False).split(":")[0]
        for an, att in (c.attributes or {}).items():
            slots.append({
                "name": f"{prefix}:{n}.{an}", "role": "field", "domain_class": n, "range": att.range or "string",
                "object_kind": pack.object_kind(att.range or "string")[0], "multivalued": bool(att.multivalued),
                "qualifiers": [], "identity_qualifiers": [], "subsets": [], "extract": None,
                "description": " ".join(str(att.description or "").split()) or None,
                "annotations": annotations(att),
            })
    for n in sorted(sv.all_enums()):
        e = sv.get_enum(n)
        enums.append({
            "name": sv.get_uri(e, expand=False),
            "values": [{"value": k, "description": " ".join(str(v.description or "").split()) or None,
                        "annotations": annotations(v)} for k, v in e.permissible_values.items()],
            "annotations": annotations(e),
        })
    rf = pack.rules
    pref = lambda ps: [pack.predicates[p].prefixed for p in ps]  # noqa: E731
    for r in rf.rules:
        rules.append({"rule_id": r.id, "grp": "rules", "applies_to": pref(pack.expand_applies_to(r.applies_to)),
                      "at": list(r.at), "severity": r.severity, "when_expr": r.when, "check_expr": r.check,
                      "description": " ".join(r.description.split())})
    for r in rf.guideline:
        rules.append({"rule_id": r.id, "grp": "guideline", "applies_to": pref(pack.expand_applies_to(r.applies_to)),
                      "at": ["batch", "finalize"], "severity": "warning", "when_expr": r.when, "check_expr": r.check,
                      "description": " ".join(r.description.split())})
    slots.sort(key=lambda r: r["name"])
    rules.sort(key=lambda r: r["rule_id"])
    return {"schema_class": classes, "schema_slot": slots, "schema_enum": enums, "schema_rule": rules}
