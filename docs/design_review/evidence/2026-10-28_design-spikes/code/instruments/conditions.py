"""Condition trees (D1 §7): walking, canonicalization (D5 §5.2) and structural equivalence (D7 §5.3).

Canonicalization flattens nested ``and``/``or``, collapses a one-argument ``and``/``or`` to its
argument, drops empty ones, writes ``>``/``>=`` as ``<``/``<=`` with sides swapped, sorts
``and``/``or`` arguments and ``pred`` arguments by canonical JSON (all v0 condition predicates
are symmetric: independent, identically_distributed, iid), and canonicalizes values (D1 §6.2).
``phrase`` and ``unsupported`` leaves enter keys by normalized text only (not span, not reason).
"""

from __future__ import annotations

import json
import unicodedata
from typing import Any, Callable, Iterator

import numpy as np
from scipy.optimize import linear_sum_assignment

from .batch import as_formula, ref_of
from .values import canonical_value, text_norm


def _nfc(o: Any) -> Any:
    if isinstance(o, str):
        return unicodedata.normalize("NFC", o)
    if isinstance(o, dict):
        return {_nfc(k): _nfc(v) for k, v in o.items()}
    if isinstance(o, (list, tuple)):
        return [_nfc(v) for v in o]
    return o


def canonical_json(obj: Any) -> str:
    """D1 §10.1: sorted keys, no insignificant whitespace, NFC strings (UTF-8 on encoding)."""
    return json.dumps(_nfc(obj), sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def as_dict(n: Any) -> Any:
    if hasattr(n, "model_dump"):
        return n.model_dump(exclude_none=True)
    return n


def iter_nodes(tree: Any) -> Iterator[dict]:
    tree = as_dict(tree)
    if not tree:
        return
    yield tree
    op = tree.get("op")
    if op in ("and", "or"):
        for a in tree.get("args", []):
            yield from iter_nodes(a)
    elif op == "not":
        yield from iter_nodes(tree.get("arg"))
    elif op == "forall":
        yield from iter_nodes(tree.get("body"))


def claim_refs(tree: Any) -> list[str]:
    return [n["ref"] for n in iter_nodes(tree) if n.get("op") == "claim"]


def has_uninterpreted(tree: Any) -> bool:
    """INV-09: the tree has a ``phrase`` or ``unsupported`` leaf."""
    return any(n.get("op") in ("phrase", "unsupported") for n in iter_nodes(tree))


def formula_positions(tree: Any) -> Iterator[tuple[str, dict]]:
    """(kind, formula/set value dict) for every formula or set position of a tree."""
    for n in iter_nodes(tree):
        op = n.get("op")
        if op == "member":
            yield "formula", as_formula(n["x"])
            yield "set", as_formula(n["set"], "set")
        elif op == "cmp":
            yield "formula", as_formula(n["lhs"])
            yield "formula", as_formula(n["rhs"])
        elif op == "forall":
            yield "formula", as_formula(n["var"])
            yield "set", as_formula(n["set"], "set")
        elif op == "pred":
            for a in n.get("args", []):
                a = as_dict(a)
                if isinstance(a, dict) and a.get("t") == "formula":
                    yield "formula", a


def entity_positions(tree: Any) -> Iterator[str]:
    for n in iter_nodes(tree):
        if n.get("op") == "pred":
            for a in n.get("args", []):
                a = as_dict(a)
                if isinstance(a, str) or (isinstance(a, dict) and "ref" in a):
                    r = ref_of(a)
                    if r:
                        yield r


_FLIP = {">": "<", ">=": "<="}


def normalize_tree(tree: Any) -> dict | None:
    """Structural normalization without value canonicalization (used by equivalence)."""
    tree = as_dict(tree)
    if not tree:
        return None
    op = tree.get("op")
    if op in ("and", "or"):
        args = []
        for a in tree.get("args", []):
            na = normalize_tree(a)
            if na is None:
                continue
            if na.get("op") == op:
                args.extend(na["args"])
            else:
                args.append(na)
        if not args:
            return None
        if len(args) == 1:
            return args[0]
        return {"op": op, "args": args}
    if op == "not":
        inner = normalize_tree(tree.get("arg"))
        return {"op": "not", "arg": inner}
    if op == "cmp" and tree["rel"] in _FLIP:
        return {"op": "cmp", "rel": _FLIP[tree["rel"]], "lhs": tree["rhs"], "rhs": tree["lhs"]}
    if op == "forall":
        return {**tree, "body": normalize_tree(tree.get("body"))}
    return tree


def canonical_condition(
    tree: Any,
    macros: dict | None = None,
    claim_key: Callable[[str], Any] | None = None,
    ref_key: Callable[[str], Any] | None = None,
) -> Any:
    """D5 §5.2 canonical tree: claim refs replaced by ``claim_key(ref)``, entity refs by
    ``ref_key(ref)``, values canonical, arguments sorted by canonical JSON."""
    ck = claim_key or (lambda r: r)
    rk = ref_key or (lambda r: r)

    def canon(n):
        if n is None:
            return None
        op = n["op"]
        if op in ("and", "or"):
            args = sorted((canon(a) for a in n["args"]), key=canonical_json)
            return {"op": op, "args": args}
        if op == "not":
            return {"op": "not", "arg": canon(n["arg"])}
        if op == "claim":
            return {"op": "claim", "ref": ck(n["ref"])}
        if op == "member":
            return {"op": "member", "x": canonical_value(as_formula(n["x"]), macros),
                    "set": canonical_value(as_formula(n["set"], "set"), macros)}
        if op == "cmp":
            return {"op": "cmp", "rel": n["rel"], "lhs": canonical_value(as_formula(n["lhs"]), macros),
                    "rhs": canonical_value(as_formula(n["rhs"]), macros)}
        if op == "pred":
            args = []
            for a in n.get("args", []):
                a = as_dict(a)
                if isinstance(a, dict) and a.get("t") == "formula":
                    args.append(canonical_value(a, macros))
                else:
                    args.append({"ref": rk(ref_of(a))})
            return {"op": "pred", "name": n["name"], "args": sorted(args, key=canonical_json)}
        if op == "forall":
            return {"op": "forall", "var": canonical_value(as_formula(n["var"]), macros),
                    "set": canonical_value(as_formula(n["set"], "set"), macros), "body": canon(n["body"])}
        if op == "phrase":
            return {"op": "phrase", "text": text_norm(n["text"])}
        if op == "unsupported":
            return {"op": "unsupported", "text": text_norm(n["text"])}
        return n

    return canon(normalize_tree(tree))


def _perfect_match(xs: list, ys: list, eq: Callable[[Any, Any], bool]) -> bool:
    if len(xs) != len(ys):
        return False
    if not xs:
        return True
    m = np.zeros((len(xs), len(ys)))
    for i, x in enumerate(xs):
        for j, y in enumerate(ys):
            m[i, j] = 1.0 if eq(x, y) else 0.0
    r, c = linear_sum_assignment(-m)
    return bool(m[r, c].sum() == len(xs))


def trees_equivalent(
    ta: Any,
    tb: Any,
    *,
    value_eq: Callable[[dict, dict], bool],
    claim_eq: Callable[[str, str], bool],
    ref_eq: Callable[[str, str], bool],
    span_eq: Callable[[dict, dict], bool],
) -> bool:
    """D7 §5.3: both trees canonicalized; leaves matched one-to-one."""
    a, b = normalize_tree(ta), normalize_tree(tb)

    def eq(x, y) -> bool:
        if x is None or y is None:
            return x is None and y is None
        if x["op"] != y["op"]:
            return False
        op = x["op"]
        if op in ("and", "or"):
            return _perfect_match(x["args"], y["args"], eq)
        if op == "not":
            return eq(x["arg"], y["arg"])
        if op == "claim":
            return claim_eq(x["ref"], y["ref"])
        if op == "member":
            return value_eq(as_formula(x["x"]), as_formula(y["x"])) and value_eq(
                as_formula(x["set"], "set"), as_formula(y["set"], "set"))
        if op == "cmp":
            same = x["rel"] == y["rel"] and value_eq(as_formula(x["lhs"]), as_formula(y["lhs"])) and value_eq(
                as_formula(x["rhs"]), as_formula(y["rhs"]))
            if not same and x["rel"] in ("=", "!=") and x["rel"] == y["rel"]:
                same = value_eq(as_formula(x["lhs"]), as_formula(y["rhs"])) and value_eq(
                    as_formula(x["rhs"]), as_formula(y["lhs"]))
            return same
        if op == "pred":
            def arg_eq(p, q):
                p, q = as_dict(p), as_dict(q)
                pf = isinstance(p, dict) and p.get("t") == "formula"
                qf = isinstance(q, dict) and q.get("t") == "formula"
                if pf != qf:
                    return False
                return value_eq(p, q) if pf else ref_eq(ref_of(p), ref_of(q))
            return x["name"] == y["name"] and _perfect_match(x["args"], y["args"], arg_eq)
        if op == "forall":
            return (value_eq(as_formula(x["var"]), as_formula(y["var"]))
                    and value_eq(as_formula(x["set"], "set"), as_formula(y["set"], "set"))
                    and eq(x["body"], y["body"]))
        if op in ("phrase", "unsupported"):
            return span_eq(x, y)
        return False

    return eq(a, b)
