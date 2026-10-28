"""Rules (D2 §7.4; D5 §8.2): the rule-language helper, the generic view builder over the core keyed
candidate, and the rule compiler and runner for both call sites.

- **Language helper.** Every expression is compiled in its own ``rule_engine.Context`` with a type
  resolver generated from the schema version, OBJECT symbols read through ``getattr``, mapping
  dot-access off, UTC; ``$now``, ``$today`` and ``$random`` are rejected from the compiled symbol set.
  Tables become typed ``$`` builtins, with ``$enums`` (every schema enum) and ``$is_a`` (inheritance).
- **Candidates.** One core type, ``Candidate``, which a batch (call site ``batch``: ids are local refs,
  keys null) and a run pool (call site ``finalize``: ids are keys) both adapt into.
- **View builder.** One generic builder computes the domain-free attributes (groups, statement facts,
  bindings, flattened condition nodes, claim refs, premises, the "given as a parameter value" pair
  through ``ci:param_map``, slot competitors, alternatives) and compiles the pack's ``views:``
  declarations; no predicate or class is named here.
- **Readers.** At ``batch`` no math grammar runs (parse fields are null); at ``finalize`` the caller
  hands the builder each value's parse status and kind as data (``parse_info``).
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from functools import cached_property
from typing import Any, Callable

import rule_engine
from rule_engine import Context, DataType, Rule
from rule_engine.builtins import Builtins

from .pack import Pack

NONDETERMINISTIC = {"now", "today", "random"}
_BARE = re.compile(r"[A-Za-z]+(_\{?\w+\}?)?")
_INDEX = re.compile(r"_\{?([A-Za-z])\}?")

# ----------------------------------------------------------------------------- the core candidate


@dataclass
class EntityInfo:
    id: str
    key: str | None
    type: str
    label: str
    symbol: str | None
    identity: dict[str, str]


@dataclass
class Candidate:
    """The core keyed candidate claim, the one type both call sites present to the view builder."""

    id: str
    key: str | None
    scope: str  # the batch (unit) the candidate came from; symbol facts are scoped to it
    predicate: str
    subject: str
    object_ref: str | None
    value: dict | None
    qualifiers: dict
    statement: str | None
    statement_role: str | None
    evidence_count: int
    establishment: str = "stated"


@dataclass
class CandidateSet:
    candidates: list[Candidate]
    entities: dict[str, EntityInfo]
    statements: dict[str, tuple[str | None, str]]  # id -> (key, kind)
    alternatives: list[list[str]]
    site: str
    parse_info: dict[tuple[str, str], tuple[str, str | None]] = field(default_factory=dict)  # (claim id, latex) -> (status, kind)


def _rmap(o, f: Callable[[str], str]):
    """Rewrite local refs inside qualifier trees (claim nodes, entity refs, bindings)."""
    if isinstance(o, dict):
        out = {}
        for k, v in o.items():
            if k == "ref" and isinstance(v, str):
                out[k] = f(v)
            elif k in ("entity", "claim") and isinstance(v, str) and "bind" in o:
                out[k] = f(v)
            else:
                out[k] = _rmap(v, f)
        return out
    if isinstance(o, list):
        return [_rmap(v, f) for v in o]
    return o


def from_batch(batch: dict, scope: str = "batch") -> CandidateSet:
    ents = {e["local_ref"]: EntityInfo(e["local_ref"], None, e["type"], e["label"], e.get("symbol"), dict(e.get("identity") or {}))
            for e in batch.get("entities", [])}
    sts = {s["local_ref"]: (None, s["kind"]) for s in batch.get("statements", [])}
    for s, (_, k) in sts.items():
        ents[s] = EntityInfo(s, None, "Statement", f"{k} {s}", None, {})
    cands = []
    for c in batch.get("claims", []):
        o = c["object"]
        cands.append(Candidate(
            id=c["local_ref"], key=None, scope=scope, predicate=c["predicate"], subject=c["subject"],
            object_ref=o.get("ref") if "t" not in o else None, value=o if "t" in o else None,
            qualifiers=dict(c.get("qualifiers") or {}), statement=c.get("statement"),
            statement_role=c.get("statement_role"), evidence_count=len(c.get("evidence", []))))
    return CandidateSet(cands, ents, sts, [list(a["refs"]) for a in batch.get("alternatives", [])], "batch")


def from_pool(batches: dict[str, dict], pack: Pack) -> CandidateSet:
    """A run pool at finalize: keys replace local refs. Spike stand-in for consolidation's keys:
    global entities keyed by class and casefolded label (parameters by family key and canonical
    name), local entities, statements and claims by unit and local ref."""
    ents: dict[str, EntityInfo] = {}
    sts: dict[str, tuple[str | None, str]] = {}
    cands: list[Candidate] = []
    alts: list[list[str]] = []
    for unit, b in sorted(batches.items()):
        lmap: dict[str, str] = {}
        for s in b.get("statements", []):
            lmap[s["local_ref"]] = f"stm:{unit}:{s['local_ref']}"
        glob = [e for e in b.get("entities", []) if e["scope"] == "global"]
        for e in b.get("entities", []):
            if e["scope"] == "local":
                lmap[e["local_ref"]] = f"ent:{unit}:{e['local_ref']}"
        for e in sorted(glob, key=lambda e: bool(pack.identity_keys(e["type"]))):  # families before their parameters
            if pack.identity_keys(e["type"]):
                parts = [lmap.get(e["identity"].get(k), e["identity"].get(k, "")) for k in pack.identity_keys(e["type"])]
                lmap[e["local_ref"]] = f"ent:{e['type']}:" + "/".join(parts)
            else:
                lmap[e["local_ref"]] = f"ent:{e['type']}:{' '.join(e['label'].casefold().split())}"
        for c in b.get("claims", []):
            lmap[c["local_ref"]] = f"clm:{unit}:{c['local_ref']}"
        f = lambda r: lmap.get(r, r)  # noqa: E731
        for e in b.get("entities", []):
            k = lmap[e["local_ref"]]
            ents.setdefault(k, EntityInfo(k, k, e["type"], e["label"], e.get("symbol"),
                                          {i: f(v) for i, v in (e.get("identity") or {}).items()}))
        for s in b.get("statements", []):
            k = lmap[s["local_ref"]]
            sts[k] = (k, s["kind"])
            ents[k] = EntityInfo(k, k, "Statement", f"{s['kind']} {k}", None, {})
        for c in b.get("claims", []):
            o = c["object"]
            k = lmap[c["local_ref"]]
            cands.append(Candidate(
                id=k, key=k, scope=unit, predicate=c["predicate"], subject=f(c["subject"]),
                object_ref=f(o["ref"]) if "t" not in o else None, value=_rmap(o, f) if "t" in o else None,
                qualifiers=_rmap(dict(c.get("qualifiers") or {}), f), statement=f(c["statement"]) if c.get("statement") else None,
                statement_role=c.get("statement_role"), evidence_count=len(c.get("evidence", []))))
        alts += [[f(r) for r in a["refs"]] for a in b.get("alternatives", [])]
    return CandidateSet(cands, ents, sts, alts, "finalize")


# ------------------------------------------------------------------------------------- views


class V:
    """A plain view object; rule-engine reads it through getattr."""

    def __init__(self, **kw):
        self.__dict__.update(kw)


def _nodes(tree):
    if isinstance(tree, dict) and "op" in tree:
        yield tree
        for a in tree.get("args") or []:
            if isinstance(a, dict) and "op" in a:
                yield from _nodes(a)
        for k in ("arg", "body"):
            if isinstance(tree.get(k), dict):
                yield from _nodes(tree[k])


def _values(o):
    if isinstance(o, dict):
        if o.get("t") in ("formula", "set"):
            yield o
        for v in o.values():
            yield from _values(v)
    elif isinstance(o, list):
        for v in o:
            yield from _values(v)


def _node_view(n):
    return V(op=n["op"], ref=n.get("ref"), name=n.get("name"), rel=n.get("rel"),
             x_latex=(n.get("x") or {}).get("latex", "").strip() if isinstance(n.get("x"), dict) else None)


class ViewBuilder:
    def __init__(self, pack: Pack):
        self.pack = pack

    def _entity(self, cs: CandidateSet, ref: str | None):
        if ref is None:
            return None
        e = cs.entities.get(ref)
        if e is None:
            return V(id=ref, key=None, type="", label="", symbol=None, identity={}, index_symbols=())
        return V(id=e.id, key=e.key, type=e.type, label=e.label, symbol=e.symbol, identity=dict(e.identity),
                 index_symbols=tuple(sorted(set(_INDEX.findall(e.symbol or "")))))

    def _gives(self, c: Candidate) -> set[str]:
        """Symbols the claim gives as parameter values: bare symbols among the values of its
        ci:param_map qualifier, when the claim is a supposition or setup value (statement_role premise or
        example_value), the givers guideline §10.7 row 3 means ("Suppose that X has … with mean μ")."""
        pm = self.pack.predicates[c.predicate].param_map
        if c.statement_role not in ("premise", "example_value"):
            return set()
        out = set()
        for v in ((c.qualifiers.get(pm) or {}).values() if pm else []):
            if isinstance(v, dict) and v.get("t") == "formula":
                lx = v.get("latex", "").strip().lstrip("\\")
                if _BARE.fullmatch(lx):
                    out.add(lx)
        return out

    def build(self, cs: CandidateSet) -> list[V]:
        p = self.pack
        by_scope: dict[str, list[Candidate]] = {}
        for c in cs.candidates:
            by_scope.setdefault(c.scope, []).append(c)
        gives = {c.id: self._gives(c) for c in cs.candidates}
        alt_of: dict[str, set[str]] = {}
        for g in cs.alternatives:
            for r in g:
                alt_of.setdefault(r, set()).update(x for x in g if x != r)
        views = []
        for c in cs.candidates:
            pi = p.predicates[c.predicate]
            st_kind = cs.statements.get(c.statement, (None, None))[1] if c.statement else None
            scope = by_scope[c.scope]
            qual = {q: None for q in p.qualifiers}
            for q, v in c.qualifiers.items():
                qi = p.qualifiers[q]
                if qi.object_kind == "map":
                    qual[q] = {k: (x.get("latex") if isinstance(x, dict) else x) for k, x in v.items()}
                elif qi.object_kind == "condition":
                    qual[q] = tuple(_node_view(n) for n in _nodes(v))
                elif qi.object_kind == "entity":
                    qual[q] = v["ref"]
                elif qi.object_kind in ("formula", "set"):
                    qual[q] = v.get("latex")
                elif qi.object_kind == "phrase":
                    qual[q] = v.get("text")
                elif q == "scope" and isinstance(v, dict):
                    qual[q] = v.get("extent")
                elif isinstance(v, (str, type(None))):
                    qual[q] = v
                else:
                    qual[q] = str(v)
            qual["modality"] = qual.get("modality") or "asserted"
            qual["polarity"] = qual.get("polarity") or "positive"
            nodes = list(_nodes(c.qualifiers.get("conditions")))
            claim_refs = tuple(n["ref"] for n in nodes if n["op"] == "claim")
            bindings = []
            for fv in _values({"o": c.value, "q": c.qualifiers}):
                for sym, b in (fv.get("symbols") or {}).items():
                    bindings.append(V(symbol=sym, bind=b["bind"], entity=b.get("entity"), claim=b.get("claim"), param=b.get("param")))
            value = None
            if c.value is not None:
                lx = c.value.get("latex")
                status, mk = cs.parse_info.get((c.id, lx), (None, None)) if lx is not None else (None, None)
                value = V(t=c.value["t"], latex=lx, v=c.value.get("v") if isinstance(c.value.get("v"), str) else None,
                          enum=c.value.get("enum"), slot_kind=pi.object_kind, parse=status, math_kind=mk)
            premises = tuple(o.id for o in scope if o.statement_role == "premise"
                             and (o.statement == c.statement or cs.statements.get(o.statement, (None, None))[1] == "assumption"))
            given_others = set()
            for o in scope:
                if o.id != c.id:
                    given_others |= gives[o.id]
            view = V(
                id=c.id, key=c.key, predicate=pi.prefixed, groups=tuple(pi.subsets),
                subject=self._entity(cs, c.subject), object=self._entity(cs, c.object_ref), value=value,
                qualifiers=V(**qual), statement=V(id=c.statement, key=cs.statements[c.statement][0], kind=st_kind) if c.statement in cs.statements else None,
                statement_kind=st_kind, statement_role=c.statement_role, establishment=c.establishment,
                bindings=tuple(bindings), condition_nodes=tuple(_node_view(n) for n in nodes), claim_refs=claim_refs,
                statement_premises=premises, gives_symbols=tuple(sorted(gives[c.id])), given_by_others=tuple(sorted(given_others)),
                same_slot=tuple(o.id for o in scope if o.id != c.id and o.predicate == c.predicate and o.subject == c.subject
                                and o.statement == c.statement),
                alternative_of=tuple(sorted(alt_of.get(c.id, ()))),
                evidence_count=c.evidence_count, unresolved_symbols=sum(b.bind == "unresolved" for b in bindings),
                _candidate=c,
            )
            views.append(view)
        self._pack_views(cs, views)
        return views

    def _pack_views(self, cs: CandidateSet, views: list[V]) -> None:
        """Compile the pack's views: declarations: source claims matched on an entity, a field projected.
        At batch the pool is the batch; at finalize it is the run (any status except rejected)."""
        p = self.pack
        for name, d in p.rules.views.items():
            applies = set(p.expand_applies_to(d.applies_to))
            src = p.expand_applies_to(d.source)[0]
            sources = [v for v in views if v._candidate.predicate == src]
            for v in views:
                vals: list[str] = []
                if v._candidate.predicate in applies:
                    want = getattr(v, d.match["claim"])
                    for s in sources:
                        got = getattr(s, d.match["source"])
                        if want is not None and got is not None and got.id == want.id:
                            x: Any = s
                            for part in d.project.split("."):
                                x = x.get(part) if isinstance(x, dict) else getattr(x, part, None)
                                if x is None:
                                    break
                            if isinstance(x, str):
                                vals.append(x)
                setattr(v, name, tuple(sorted(set(vals))))


# --------------------------------------------------------------------------------- the language


class Language:
    """Typed contexts generated from the schema version, one per compiled expression."""

    def __init__(self, pack: Pack, function_form: bool = False):
        self.pack = pack
        self.function_form = function_form

    @cached_property
    def types(self) -> dict:
        p, T = self.pack, DataType
        S, NS = T.STRING, T.NULLABLE(T.STRING)
        node = T.OBJECT("Node", attributes={"op": S, "ref": NS, "name": NS, "rel": NS, "x_latex": NS})
        ent = T.OBJECT("Entity", attributes={"id": S, "key": NS, "type": S, "label": S, "symbol": NS,
                                             "identity": T.MAPPING(S, S), "index_symbols": T.ARRAY(S)})
        val = T.OBJECT("Value", attributes={"t": S, "latex": NS, "v": NS, "enum": NS, "slot_kind": S, "parse": NS, "math_kind": NS})
        st = T.OBJECT("Statement", attributes={"id": S, "key": NS, "kind": S})
        bnd = T.OBJECT("Binding", attributes={"symbol": S, "bind": S, "entity": NS, "claim": NS, "param": NS})
        qa = {}
        for q, qi in p.qualifiers.items():
            if q in ("modality", "polarity"):
                qa[q] = S
            elif qi.object_kind == "map":
                qa[q] = T.NULLABLE(T.MAPPING(S, S))
            elif qi.object_kind == "condition":
                qa[q] = T.NULLABLE(T.ARRAY(node))
            else:
                qa[q] = NS
        quals = T.OBJECT("Qualifiers", attributes=qa)
        attrs = {
            "id": S, "key": NS, "predicate": S, "groups": T.ARRAY(S), "subject": ent, "object": T.NULLABLE(ent),
            "value": T.NULLABLE(val), "qualifiers": quals, "statement": T.NULLABLE(st), "statement_kind": NS,
            "statement_role": NS, "establishment": S, "bindings": T.ARRAY(bnd), "condition_nodes": T.ARRAY(node),
            "claim_refs": T.ARRAY(S), "statement_premises": T.ARRAY(S), "gives_symbols": T.ARRAY(S),
            "given_by_others": T.ARRAY(S), "same_slot": T.ARRAY(S), "alternative_of": T.ARRAY(S),
            "evidence_count": T.FLOAT, "unresolved_symbols": T.FLOAT,
        }
        if not self.function_form:
            for name in p.rules.views:
                attrs[name] = T.ARRAY(S)
        return {"claim": T.OBJECT("Claim", attributes=attrs)}

    def builtins(self, pool_fn: Callable[[str], tuple] | None = None) -> tuple[dict, dict]:
        p, T = self.pack, DataType
        values: dict[str, Any] = {"enums": {k: tuple(v) for k, v in p.enums.items()},
                                  "is_a": lambda c, t: p.is_a(c, t)}
        vtypes: dict[str, Any] = {"enums": T.MAPPING(T.STRING, T.ARRAY(T.STRING)),
                                  "is_a": T.FUNCTION("is_a", return_type=T.BOOLEAN, argument_types=(T.STRING, T.STRING))}
        for name, table in p.rules.tables.items():
            if all(isinstance(v, list) for v in table.values()):
                values[name] = {k: tuple(v) for k, v in table.items()}
                vtypes[name] = T.MAPPING(T.STRING, T.ARRAY(T.STRING))
            else:
                values[name] = dict(table)
                vtypes[name] = T.MAPPING(T.STRING, T.STRING)
        if self.function_form:
            for name in p.rules.views:
                values[name] = pool_fn or (lambda _id: ())
                vtypes[name] = T.FUNCTION(name, return_type=T.ARRAY(T.STRING), argument_types=(T.STRING,))
        return values, vtypes

    def compile(self, expr: str, pool_fn=None) -> Rule:
        ctx = Context(type_resolver=rule_engine.type_resolver_from_dict(self.types),
                      mapping_attribute_lookup=False, default_timezone="utc")
        values, vtypes = self.builtins(pool_fn)
        ctx.builtins = Builtins.from_defaults(values=values, value_types=vtypes, timezone=ctx.default_timezone)
        rule = Rule(expr, context=ctx)
        bad = ctx.symbols & NONDETERMINISTIC
        if bad:
            raise rule_engine.errors.RuleSyntaxError(f"nondeterministic builtin(s) {sorted(bad)} rejected")
        return rule


@dataclass
class Compiled:
    id: str
    grp: str
    severity: str
    at: tuple[str, ...]
    applies: frozenset[str]
    when: Rule
    check: Rule


def compile_rules(pack: Pack, lang: Language | None = None) -> list[Compiled]:
    lang = lang or Language(pack)
    out = []
    for r in pack.rules.rules:
        out.append(Compiled(r.id, "rules", r.severity, tuple(r.at), frozenset(pack.expand_applies_to(r.applies_to)),
                            lang.compile(r.when), lang.compile(r.check)))
    for r in pack.rules.guideline:
        out.append(Compiled(r.id, "guideline", "warning", ("batch", "finalize"), frozenset(pack.expand_applies_to(r.applies_to)),
                            lang.compile(r.when), lang.compile(r.check)))
    return out


def run(rules: list[Compiled], views: list[V], site: str) -> list[dict]:
    """One row per (rule, claim) the rule applies to at this site: result pass | fire."""
    out = []
    for r in rules:
        if site not in r.at:
            continue
        for v in views:
            if v._candidate.predicate not in r.applies:
                continue
            if not r.when.matches({"claim": v}):
                continue
            ok = r.check.matches({"claim": v})
            out.append({"rule": r.id, "grp": r.grp, "severity": r.severity, "site": site, "claim": v.id,
                        "scope": v._candidate.scope, "result": "pass" if ok else "fire"})
    return out
