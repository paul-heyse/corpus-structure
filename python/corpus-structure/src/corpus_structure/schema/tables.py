"""The schema-table compiler (P0-S-1; D2 §7.1; D3 §3; schema and rules §3.3).

Rows for `meta.schema_class`, `schema_slot`, `schema_enum` and `schema_rule` in D3's column
names, without `schema_version_id` (registration adds it), and the per-version member rows of the
version-scoped sets (`meta.statement_kind`, `meta.claim_modality`). Every name is prefixed.

Slot rows cover predicates and qualifiers (`ci:role`), identity slots (in a class's
`unique_keys`), and fields; class-local attributes are named `<prefix>:<Class>.<attribute>`,
because D3's key cannot hold two attributes of one name in different classes. A slot's
`annotations` hold its scalar `ci:` declarations, its key role and case, and the native metaslots
the design reads (`symmetric`, `transitive`, `inverse`): the inference declarations a later
recursive-SQL compiler reads. `derive:` entries become rule rows of group `derive`.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from corpus_structure.schema.lookup import SchemaLookup
from corpus_structure.schema.model import ci_annotations
from corpus_structure.schema.pack import Pack, PackError

ROLE_ANNOTATIONS = frozenset({"ci:role", "ci:qualifiers", "ci:identity_qualifiers", "ci:extract"})


def _one(text: Any) -> str | None:
    return " ".join(str(text or "").split()) or None


def expand_applies_to(lookup: SchemaLookup, applies_to: str | Sequence[str]) -> list[str]:
    """The prefixed predicates an `applies_to` names: `any`, `subset:<name>`, or prefixed
    predicates; an unknown name is a `PackError` (D2 §7.4)."""
    items = [applies_to] if isinstance(applies_to, str) else list(applies_to)
    by_prefixed = {p.prefixed for p in lookup.predicates.values()}
    out: set[str] = set()
    problems = []
    for item in items:
        if item == "any":
            out |= by_prefixed
        elif item.startswith("subset:"):
            name = item.split(":", 1)[1]
            if name not in lookup.subsets:
                problems.append(f"applies_to names unknown subset {name!r}")
                continue
            out |= {lookup.predicates[p].prefixed for p in lookup.subsets[name][1]}
        elif item in by_prefixed:
            out.add(item)
        else:
            problems.append(f"applies_to names unknown predicate {item!r}")
    if problems:
        raise PackError(problems)
    return sorted(out)


def _class_kind(view: Any, name: str) -> str:
    c = view.get_class(name)
    ancestors = view.class_ancestors(name)
    if c.abstract or c.mixin:
        return "abstract"
    if "Entity" in ancestors and name != "Entity":
        return "entity"
    return "value"


def schema_tables(packs: Sequence[Pack], lookup: SchemaLookup) -> dict[str, list[dict[str, Any]]]:
    """The `tables` artifact body (module doc)."""
    classes: dict[str, dict[str, Any]] = {}
    slots: dict[str, dict[str, Any]] = {}
    enums: dict[str, dict[str, Any]] = {}
    identity = {s for e in lookup.entity_classes.values() for s in e.identity_keys}
    for pack in packs:
        view = pack.view

        def uri(element: Any, view: Any = view) -> str:
            return str(view.get_uri(element, expand=False))

        for n in sorted(view.all_classes()):
            c = view.get_class(n)
            a = dict(ci_annotations(c))
            for key in ("title", "mixins", "abstract", "mixin"):
                value = getattr(c, key)
                if value:
                    a[key] = (
                        list(value) if key == "mixins" else (str(value) if key == "title" else True)
                    )
            if c.examples:
                a["examples"] = [str(e.value) for e in c.examples]
            entity = lookup.entity_classes.get(str(n))
            classes[uri(c)] = {
                "name": uri(c),
                "parent": uri(view.get_class(c.is_a)) if c.is_a else None,
                "kind": _class_kind(view, str(n)),
                "scope": entity.scope if entity else None,
                "identity_keys": list(entity.identity_keys) if entity else [],
                "description": _one(c.description),
                "annotations": dict(sorted(a.items())),
            }
            prefix = uri(c).split(":")[0]
            for an, att in (c.attributes or {}).items():
                name = f"{prefix}:{n}.{an}"
                slots[name] = {
                    "name": name,
                    "role": "field",
                    "domain_class": uri(c),
                    "range": str(att.range or "string"),
                    "object_kind": None,
                    "multivalued": bool(att.multivalued),
                    "qualifiers": [],
                    "identity_qualifiers": [],
                    "subsets": [],
                    "extract": None,
                    "description": _one(att.description),
                    "annotations": dict(sorted(ci_annotations(att).items())),
                }
        for n in sorted(view.all_slots(attributes=False)):  # attributes are rowed above
            s = view.get_slot(n)
            a = ci_annotations(s)
            name = uri(s)
            p = lookup.predicates.get(str(n))
            q = lookup.qualifiers.get(str(n))
            role = a.get("ci:role") or ("identity" if name in identity else "field")
            extra = {k: v for k, v in a.items() if k not in ROLE_ANNOTATIONS}
            for meta in ("symmetric", "transitive"):
                if getattr(s, meta):
                    extra[meta] = True
            if s.inverse:
                extra["inverse"] = str(view.get_uri(view.get_slot(s.inverse), expand=False))
            if s.ifabsent:
                extra["ifabsent"] = str(s.ifabsent)
            ind = view.induced_slot(n)
            slots[name] = {
                "name": name,
                "role": role,
                "domain_class": uri(view.get_class(ind.domain)) if ind.domain else None,
                "range": str(ind.range) if ind.range else None,
                "object_kind": p.object_kind if p else (q.object_kind if q else None),
                "multivalued": bool(ind.multivalued),
                "qualifiers": [lookup.qualifiers[x].prefixed for x in p.qualifiers] if p else [],
                "identity_qualifiers": (
                    [lookup.qualifiers[x].prefixed for x in p.identity_qualifiers] if p else []
                ),
                "subsets": sorted(str(x) for x in s.in_subset or ()),
                "extract": a.get("ci:extract"),
                "description": _one(s.description),
                "annotations": dict(sorted(extra.items())),
            }
        for n in sorted(view.all_enums()):
            e = view.get_enum(n)
            enums[uri(e)] = {
                "name": uri(e),
                "values": [
                    {
                        "value": str(k),
                        "description": _one(v.description),
                        "annotations": ci_annotations(v),
                        "properties": sorted(str(x) for x in v.in_subset or ()),
                    }
                    for k, v in (e.permissible_values or {}).items()
                ],
                "annotations": ci_annotations(e),
            }
    rules: list[dict[str, Any]] = []
    for pack in packs:
        for r in pack.rules.rules:
            rules.append(
                {
                    "rule_id": r.id,
                    "grp": "rules",
                    "applies_to": expand_applies_to(lookup, r.applies_to),
                    "at": list(r.at),
                    "severity": r.severity,
                    "when_expr": r.when,
                    "check_expr": r.check,
                    "description": _one(r.description),
                }
            )
        for g in pack.rules.guideline:
            rules.append(
                {
                    "rule_id": g.id,
                    "grp": "guideline",
                    "applies_to": expand_applies_to(lookup, g.applies_to),
                    "at": ["batch", "finalize"],
                    "severity": "warning",
                    "when_expr": g.when,
                    "check_expr": g.check,
                    "description": _one(g.description),
                }
            )
        for d in pack.rules.derive:
            rules.append(
                {
                    "rule_id": d.id,
                    "grp": "derive",
                    "applies_to": expand_applies_to(lookup, d.sources),
                    "at": [],
                    "severity": None,
                    "when_expr": d.when,
                    "check_expr": None,
                    "description": _one(d.description),
                }
            )
    members = {
        "statement_kind": [
            {"value": m.stored, "properties": sorted(m.properties)}
            for m in lookup.version_sets["StatementKind"].members
        ],
        "claim_modality": [
            {"value": m.stored, "properties": sorted(m.properties)}
            for m in lookup.version_sets["ClaimModality"].members
        ],
    }
    return {
        "schema_class": [classes[k] for k in sorted(classes)],
        "schema_slot": [slots[k] for k in sorted(slots)],
        "schema_enum": [enums[k] for k in sorted(enums)],
        "schema_rule": sorted(rules, key=lambda r: r["rule_id"]),
        **members,
    }
