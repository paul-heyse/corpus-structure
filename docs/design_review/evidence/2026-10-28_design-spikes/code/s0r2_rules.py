"""Guideline v1 rules that code can check on a model-facing batch (s0r2/guideline_v1.md).

    rule_warnings(batch) -> list[str]

Checked (approximations of the rules): statement role by statement kind (§10.3), modality by role (§10.6), which claims carry a
condition tree and what it may hold (§10.7 rules 1–4), formulas that define a variable exclude it
(§10.7), symbol-map keys without backslash, and binding priority (a value given in another
`has_distribution` claim binds `param_of`, not `free` or `family_param`). Warnings, not errors:
a rule the checker cannot see (restrictions repeated in each dependent claim, which premises a
claim depends on) stays the annotator's.
"""

from __future__ import annotations

import re

STRUCTURAL = {"defines", "proves", "refers_to", "follows_from"}
FORM = {"defined_as", "construction_formula", "definition_formula", "transformation_of", "has_parameter",
        "parameter_domain", "parameter_role", "derived_parameter", "identical_parameter", "special_case_of"}
FAMILY = {"has_parameter", "parameter_domain", "parameter_role", "derived_parameter", "identical_parameter",
          "construction_formula", "transformation_of", "special_case_of"}
ROLES = {  # statement kind -> roles a non-structural claim may take
    "definition": {"definiens", "premise"},
    "theorem": {"premise", "conclusion", "definiens"},
    "proposition": {"premise", "conclusion", "definiens"},
    "corollary": {"premise", "conclusion", "definiens"},
    "remark": {"premise", "conclusion", "definiens", None},
    "example": {"example_value"},
    "exercise": {"example_value"},
    "convention": {None},
    "assumption": {"premise"},
    "proof": set(),
    "solution": set(),
}
MODALITY = {"premise": "supposed", "definiens": "defined", "conclusion": "asserted", "example_value": "exemplified"}


def _nodes(tree):
    if not tree:
        return
    yield tree
    for a in tree.get("args") or []:
        yield from _nodes(a)
    if isinstance(tree.get("arg"), dict):
        yield from _nodes(tree["arg"])


def _values(obj):
    """Every tagged value (dict with `t`) inside obj."""
    if isinstance(obj, dict):
        if "t" in obj:
            yield obj
        for v in obj.values():
            yield from _values(v)
    elif isinstance(obj, list):
        for v in obj:
            yield from _values(v)


def _index_symbols(batch, subject):
    ent = next((e for e in batch.get("entities", []) if e.get("local_ref") == subject), None)
    sym = (ent or {}).get("symbol") or ""
    return set(re.findall(r"_\{?([A-Za-z])\}?", sym))


def rule_warnings(batch: dict) -> list[str]:
    out = []
    kinds = {s["local_ref"]: s.get("kind") for s in batch.get("statements", [])}
    claims = batch.get("claims", [])
    given = {}  # symbol -> claims whose has_distribution param_values give it as a value
    for c in claims:
        if c.get("predicate") == "has_distribution" and c.get("statement_role") in ("premise", "example_value"):
            for v in ((c.get("qualifiers") or {}).get("param_values") or {}).values():
                if isinstance(v, dict) and v.get("t") == "formula":
                    lx = v.get("latex", "").strip().lstrip("\\")
                    if re.fullmatch(r"[A-Za-z]+(_\{?\w+\}?)?", lx):
                        given.setdefault(lx, set()).add(c["local_ref"])
    for c in claims:
        ref, pred = c.get("local_ref"), c.get("predicate")
        q = c.get("qualifiers") or {}
        role, mod, kind = c.get("statement_role"), q.get("modality", "asserted"), kinds.get(c.get("statement"))
        where = f"{ref} ({pred})"
        if pred in STRUCTURAL:
            if role is not None:
                out.append(f"{where}: structural claims take no statement_role (§10.3)")
            if mod != "asserted":
                out.append(f"{where}: structural claims are asserted (§10.6)")
        else:
            if kind in ROLES and role not in ROLES[kind]:
                out.append(f"{where}: role {role!r} is not one a {kind} gives (§10.3: {sorted(map(str, ROLES[kind]))})")
            if role in MODALITY and mod != MODALITY[role]:
                out.append(f"{where}: a {role} has modality {MODALITY[role]!r}, not {mod!r} (§10.6)")
        nodes = list(_nodes(q.get("conditions")))
        claim_nodes = [n for n in nodes if n.get("op") == "claim"]
        if pred in STRUCTURAL and nodes:
            out.append(f"{where}: structural claims carry no conditions (§10.7 rule 4)")
        elif role in ("premise", "example_value"):
            idx = _index_symbols(batch, c.get("subject"))
            bad = [n for n in nodes if n.get("op") not in ("and", "member")
                   or (n.get("op") == "member" and (n.get("x") or {}).get("latex", "").strip() not in idx)]
            if bad:
                out.append(f"{where}: a {role} carries no conditions except its index range; move restrictions "
                           f"to the claims that depend on it (§10.7 rule 1)")
        elif pred in FORM and claim_nodes:
            out.append(f"{where}: a formula or family-structure claim carries no claim nodes (§10.7 rule 2)")
        elif pred not in FORM and pred not in STRUCTURAL:
            premises = [p["local_ref"] for p in claims if p.get("statement_role") == "premise"
                        and (p.get("statement") == c.get("statement") or kinds.get(p.get("statement")) == "assumption")]
            missing = [p for p in premises if p not in {n.get("ref") for n in claim_nodes}]
            if premises and len(missing) == len(premises):
                out.append(f"{where}: references none of the premises {premises} (§10.7 rule 3)")
        if pred == "parameter_role":
            ent = next((e for e in batch.get("entities", []) if e.get("local_ref") == c.get("subject")), {})
            if (c.get("object") or {}).get("v") and (c.get("object") or {}).get("v") == (ent.get("identity") or {}).get("canonical_name"):
                out.append(f"{where}: parameter_role only when the role differs from the canonical name (§10.4)")
        if pred in ("defined_as", "construction_formula"):
            obj = c.get("object") or {}
            if isinstance(obj, dict) and re.match(r"^\s*[A-Za-z]\w*(_\{?\w+\}?)?\s*=", obj.get("latex", "")):
                out.append(f"{where}: the formula excludes the variable it defines (§10.7)")
        for v in _values(c):
            for sym, b in (v.get("symbols") or {}).items():
                if sym.startswith("\\"):
                    out.append(f"{where}: symbol key {sym!r} is written without backslash (§10.7)")
                key = sym.lstrip("\\")
                others = given.get(key, set()) - {ref}
                family_claim = pred in FAMILY and b.get("bind") == "family_param"
                if others and not family_claim and b.get("bind") in ("free", "family_param") and ref not in given.get(key, set()):
                    out.append(f"{where}: {key} is the value {sorted(others)} give to a parameter; bind param_of (§10.7)")
    return sorted(set(out))
