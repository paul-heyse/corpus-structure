"""Entity and claim alignment per unit (D7 §5.2-5.3; instruments §5.1-5.2).

``align_unit(ref, pred)`` aligns two stored-form batches of one unit: ``ref`` is the reference
(golden, trace, pass A), ``pred`` the prediction (pass B, a method). Matching is one-to-one.

Entity similarity (weights and threshold are instrument choices; D7 leaves them open):

- types must be equal, otherwise similarity 0 (never aligned);
- local entities (not statements): normalized symbol (``symbol``, else ``label``) equal -> 0.7,
  plus 0.2 when the scope segments are equal (scope mismatches stay alignable so that scope
  accuracy can be measured);
- global entities: a label or alias equal after D1 §6.2 text normalization -> 1.0; equal after
  the D2 §12.1 alias rules (rewrites, articles, head words; D5 §3.3) -> 0.9; else RapidFuzz
  ``token_sort_ratio`` >= 90 over label/alias pairs -> 0.6 + 0.2 * (ratio - 90) / 10
  (``token_set_ratio`` is not used, instruments §5.1);
- ``FamilyParameter`` (second pass, after families are aligned): family aligned and canonical
  name equal after text normalization -> 1.0; family aligned and names differing -> not aligned,
  recorded as an identity near miss; identity missing on either side -> the global label rule;
- statements: anchor overlap in characters (segment offsets supplied by the caller), else key
  overlap: any overlap -> 0.6 + 0.3 * overlap ratio + 0.1 if the kinds are equal;
- tie-breaker: +0.05 when the entities' claim evidence spans overlap.

Pairs below ``ENTITY_THRESHOLD`` (0.5) are reported unmatched.

Claims: per tier a maximum-cardinality one-to-one matching (``linear_sum_assignment`` on
1 + 0.001 * evidence overlap). Full-tier ``claim`` condition leaves are matched through the
**core-tier** claim matching, so a premise's own full-tier failure does not cascade into the
conclusions that reference it.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

import numpy as np
from rapidfuzz import fuzz
from scipy.optimize import linear_sum_assignment

from .batch import as_formula, ref_of
from .conditions import normalize_tree, trees_equivalent
from .schema_lookup import SchemaLookup
from .values import ValueComparator, canonical_symbol, text_norm

ENTITY_THRESHOLD = 0.5
W_SYMBOL, W_SCOPE, W_EVIDENCE = 0.7, 0.2, 0.05
TIERS = ("core", "full", "evidence")

# D2 §12.1 `aliases` (label normalization, D5 §3.3), copied.
_ARTICLES = ("the", "a", "an")
_HEAD_WORDS = {"DistributionFamily": ("distribution", "distributions")}
_REWRITES = ((re.compile(r"^(\w+)ly distributed$"), r"\1"), (re.compile(r"^(\w+) distributed$"), r"\1"))


def alias_norm(label: str, cls: str) -> str:
    s = text_norm(label)
    for rx, rep in _REWRITES:
        s = rx.sub(rep, s)
    words = s.split()
    if words and words[0] in _ARTICLES:
        words = words[1:]
    heads = _HEAD_WORDS.get(cls, ())
    if len(words) > 1 and words[-1] in heads:
        words = words[:-1]
    return " ".join(words)


@dataclass
class Side:
    """One side of a unit comparison."""

    batch: dict  # stored form
    segment_spans: dict[str, tuple[int, int]] = field(default_factory=dict)  # anchor key -> offsets
    sentences: list[tuple[int, int]] = field(default_factory=list)  # the unit's sentence spans
    unit: str = ""


@dataclass
class EntityPair:
    ref: str
    pred: str
    sim: float
    basis: str


@dataclass
class UnitAlignment:
    unit: str
    entity_pairs: list[EntityPair] = field(default_factory=list)
    entity_unmatched_ref: list[str] = field(default_factory=list)
    entity_unmatched_pred: list[str] = field(default_factory=list)
    identity_near_misses: list[tuple[str, str, str]] = field(default_factory=list)
    ref_claims: dict[str, dict] = field(default_factory=dict)
    pred_claims: dict[str, dict] = field(default_factory=dict)
    ref_entities: dict[str, dict] = field(default_factory=dict)
    pred_entities: dict[str, dict] = field(default_factory=dict)
    matches: dict[str, list[tuple[str, str]]] = field(default_factory=dict)
    field_failures: dict[tuple[str, str], list[str]] = field(default_factory=dict)  # core-matched pairs
    diagnostics: dict[tuple[str, str], list[str]] = field(default_factory=dict)  # bindings, extent
    alternatives_ref: list[tuple[list[str], str]] = field(default_factory=list)  # matched | ambiguity_collapsed | unmatched
    alternatives_pred: list[tuple[list[str], str]] = field(default_factory=list)
    unsupported_pairs: list[tuple[str, str]] = field(default_factory=list)
    unsupported_n: tuple[int, int] = (0, 0)
    bindings: list[dict] = field(default_factory=list)
    scopes: list[dict] = field(default_factory=list)

    @property
    def emap(self) -> dict[str, str]:
        return {p.ref: p.pred for p in self.entity_pairs}

    def cmap(self, tier: str) -> dict[str, str]:
        return dict(self.matches.get(tier, []))


def _overlap(a: tuple[int, int], b: tuple[int, int]) -> int:
    return max(0, min(a[1], b[1]) - max(a[0], b[0]))


def _primary(c: dict) -> list[tuple[int, int]]:
    return [(e["start"], e["end"]) for e in c.get("evidence", []) if e.get("role") == "primary"]


def _all_spans(c: dict) -> list[tuple[int, int]]:
    return [(e["start"], e["end"]) for e in c.get("evidence", [])]


def _entity_spans(batch: dict) -> dict[str, list[tuple[int, int]]]:
    out: dict[str, list] = {}
    for c in batch.get("claims", []):
        for r in (c.get("subject"), ref_of(c.get("object") or {})):
            if r:
                out.setdefault(r, []).extend(_primary(c))
    return out


def _assign(sim: np.ndarray, threshold: float) -> list[tuple[int, int, float]]:
    if sim.size == 0:
        return []
    r, c = linear_sum_assignment(-sim)
    return [(i, j, float(sim[i, j])) for i, j in zip(r, c) if sim[i, j] >= threshold]


class _Aligner:
    def __init__(self, ref: Side, pred: Side, lookup: SchemaLookup, comparator: ValueComparator):
        self.r, self.p = ref, pred
        self.lk = lookup
        self.cmp = comparator
        self.ua = UnitAlignment(unit=ref.unit or ref.batch.get("unit_ref", ""))
        self.ua.ref_claims = {c["local_ref"]: c for c in ref.batch.get("claims", [])}
        self.ua.pred_claims = {c["local_ref"]: c for c in pred.batch.get("claims", [])}
        self.ua.ref_entities = {e["local_ref"]: e for e in ref.batch.get("entities", [])}
        self.ua.pred_entities = {e["local_ref"]: e for e in pred.batch.get("entities", [])}
        self.espan_r, self.espan_p = _entity_spans(ref.batch), _entity_spans(pred.batch)
        self.emap: dict[str, str] = {}
        self.sentences = sorted(set(ref.sentences) | set(pred.sentences))

    # ------------------------------------------------------------------ entities

    def _labels(self, e):
        return [e.get("label", "")] + list(e.get("aliases", []))

    def _global_sim(self, a, b) -> tuple[float, str]:
        t = self.lk.bare(a["type"])
        la = {text_norm(x) for x in self._labels(a) if x}
        lb = {text_norm(x) for x in self._labels(b) if x}
        if la & lb:
            return 1.0, "label"
        if {alias_norm(x, t) for x in la} & {alias_norm(x, t) for x in lb}:
            return 0.9, "alias_rule"
        best = max((fuzz.token_sort_ratio(x, y) for x in la for y in lb), default=0)
        if best >= 90:
            return 0.6 + 0.2 * (best - 90) / 10, f"fuzzy:{best:.0f}"
        return 0.0, ""

    def _sim(self, a, b, family_pass: bool) -> tuple[float, str]:
        ta, tb = self.lk.bare(a["type"]), self.lk.bare(b["type"])
        if ta != tb:
            return 0.0, ""
        ev = W_EVIDENCE if any(_overlap(x, y) for x in self.espan_r.get(a["local_ref"], []) for y in self.espan_p.get(b["local_ref"], [])) else 0.0
        if a.get("scope") == "local" and b.get("scope") == "local":
            sa = canonical_symbol(a.get("symbol") or a.get("label"))
            sb = canonical_symbol(b.get("symbol") or b.get("label"))
            if not sa or sa != sb:
                return 0.0, ""
            same = a.get("scope_segment") is not None and a.get("scope_segment") == b.get("scope_segment")
            return W_SYMBOL + (W_SCOPE if same else 0.0) + ev, "symbol" + ("+scope" if same else "")
        if a.get("scope") != b.get("scope"):
            return 0.0, ""
        if family_pass:
            ia, ib = a.get("identity") or {}, b.get("identity") or {}
            if ia and ib and "family" in ia and "family" in ib:
                fa, fb = ref_of(ia["family"]), ref_of(ib["family"])
                if self.emap.get(fa) != fb:
                    return 0.0, ""
                na, nb = text_norm(str(ia.get("canonical_name", ""))), text_norm(str(ib.get("canonical_name", "")))
                if na == nb:
                    return 1.0 + ev, "identity"
                self.ua.identity_near_misses.append((a["local_ref"], b["local_ref"], f"canonical_name {na!r} vs {nb!r}"))
                return 0.0, ""
        s, basis = self._global_sim(a, b)
        return (s + ev, basis) if s else (0.0, "")

    def _stmt_sim(self, a, b) -> tuple[float, str]:
        def spans(side, s):
            return [side.segment_spans[k] for k in s.get("anchor", []) if k in side.segment_spans]

        sa, sb = spans(self.r, a), spans(self.p, b)
        if sa and sb:
            inter = sum(_overlap(x, y) for x in sa for y in sb)
            union = sum(e - s for s, e in sa) + sum(e - s for s, e in sb) - inter
            ratio = inter / union if union else 0.0
        else:
            ka, kb = set(a.get("anchor", [])), set(b.get("anchor", []))
            inter = len(ka & kb)
            ratio = inter / len(ka | kb) if ka | kb else 0.0
        if not inter:
            return 0.0, ""
        return 0.6 + 0.3 * ratio + (0.1 if a.get("kind") == b.get("kind") else 0.0), f"anchor:{ratio:.2f}"

    def entities(self):
        rs, ps = self.r.batch.get("statements", []), self.p.batch.get("statements", [])
        m = np.array([[self._stmt_sim(a, b)[0] for b in ps] for a in rs]) if rs and ps else np.zeros((0, 0))
        for i, j, s in _assign(m, ENTITY_THRESHOLD):
            self.ua.entity_pairs.append(EntityPair(rs[i]["local_ref"], ps[j]["local_ref"], s, self._stmt_sim(rs[i], ps[j])[1]))
        self.emap = self.ua.emap
        re_, pe = self.r.batch.get("entities", []), self.p.batch.get("entities", [])
        for family_pass in (False, True):
            ra = [e for e in re_ if (self.lk.bare(e["type"]) == "FamilyParameter") == family_pass]
            pa = [e for e in pe if (self.lk.bare(e["type"]) == "FamilyParameter") == family_pass]
            if not ra or not pa:
                continue
            m = np.array([[self._sim(a, b, family_pass)[0] for b in pa] for a in ra])
            for i, j, s in _assign(m, ENTITY_THRESHOLD):
                basis = self._sim(ra[i], pa[j], family_pass)[1]
                self.ua.entity_pairs.append(EntityPair(ra[i]["local_ref"], pa[j]["local_ref"], s, basis))
            self.emap = self.ua.emap
        matched_r = set(self.emap)
        matched_p = set(self.emap.values())
        self.ua.entity_unmatched_ref = [x["local_ref"] for x in re_ + rs if x["local_ref"] not in matched_r]
        self.ua.entity_unmatched_pred = [x["local_ref"] for x in pe + ps if x["local_ref"] not in matched_p]
        # near misses are recorded during scoring of every candidate; keep only unaligned ones
        self.ua.identity_near_misses = sorted({nm for nm in self.ua.identity_near_misses if nm[0] not in matched_r})

    # ------------------------------------------------------------------ claims

    def ref_eq(self, a, b) -> bool:
        return a is not None and self.emap.get(a) == b

    def _value_eq(self, va, vb, conds) -> bool:
        return bool(self.cmp.compare(va, vb, conds, ref_eq=self.ref_eq).equal)

    def _conds(self, a, b):
        return [x for x in ((a.get("qualifiers") or {}).get("conditions"), (b.get("qualifiers") or {}).get("conditions")) if x]

    def core(self, a, b) -> bool:
        if self.lk.bare(a["predicate"]) != self.lk.bare(b["predicate"]):
            return False
        if not self.ref_eq(a["subject"], b["subject"]):
            return False
        oa, ob = a.get("object") or {}, b.get("object") or {}
        ra, rb = ref_of(oa), ref_of(ob)
        if ra is not None or rb is not None:
            return ra is not None and rb is not None and self.ref_eq(ra, rb)
        return self._value_eq(oa, ob, self._conds(a, b))

    def _span_eq(self, x, y) -> bool:
        if None in (x.get("start"), y.get("start")):
            return text_norm(x.get("text", "")) == text_norm(y.get("text", ""))
        return _overlap((x["start"], x["end"]), (y["start"], y["end"])) > 0

    def tree_eq(self, ta, tb, conds, core_map) -> bool:
        return trees_equivalent(
            ta, tb,
            value_eq=lambda x, y: self._value_eq(x, y, conds),
            claim_eq=lambda x, y: core_map.get(x) == y,
            ref_eq=self.ref_eq,
            span_eq=self._span_eq,
        )

    def full_failures(self, a, b, core_map) -> list[str]:
        fails = []
        qa, qb = a.get("qualifiers") or {}, b.get("qualifiers") or {}
        if qa.get("modality", "asserted") != qb.get("modality", "asserted"):
            fails.append("modality")
        if qa.get("polarity", "positive") != qb.get("polarity", "positive"):
            fails.append("polarity")
        if a.get("statement_role") != b.get("statement_role"):
            fails.append("statement_role")
        conds = self._conds(a, b)
        rule = self.lk.predicate(a["predicate"])
        for name in (rule.identity_qualifiers if rule else ()):
            va, vb = qa.get(name), qb.get(name)
            if va is None and vb is None:
                continue
            if (va is None) != (vb is None):
                fails.append(f"{name}.present")
                continue
            q = self.lk.qualifier(name)
            kind, rng = q if q else (None, None)
            if kind == "map":
                if set(va) != set(vb):
                    fails.append(f"{name}.keys")
                vk = self.lk.map_value_kind(rng)
                for k in sorted(set(va) & set(vb)):
                    if vk in ("formula", "set"):
                        ok = self._value_eq(as_formula(va[k], vk), as_formula(vb[k], vk), conds)
                    else:
                        ok = text_norm(str(va[k])) == text_norm(str(vb[k]))
                    if not ok:
                        fails.append(f"{name}.values")
                        break
            elif kind == "condition":
                if not self.tree_eq(va, vb, conds, core_map):
                    fails.append(name)
            elif kind == "entity":
                if not self.ref_eq(ref_of(va), ref_of(vb)):
                    fails.append(name)
            elif kind in ("formula", "set"):
                if not self._value_eq(as_formula(va, kind), as_formula(vb, kind), conds):
                    fails.append(name)
            elif va != vb:
                fails.append(name)
        ca, cb = qa.get("conditions"), qb.get("conditions")
        if normalize_tree(ca) is not None or normalize_tree(cb) is not None:
            if not self.tree_eq(ca, cb, conds, core_map):
                fails.append("conditions")
        return fails

    def evidence_ok(self, a, b) -> bool:
        pa, pb = _primary(a), _primary(b)
        if any(_overlap(x, y) for x in pa for y in pb):
            return True
        for s in self.sentences:
            if any(_overlap(x, s) for x in pa) and any(_overlap(y, s) for y in pb):
                return True
        return False

    def _match(self, refs, preds, edge) -> list[tuple[str, str]]:
        if not refs or not preds:
            return []
        m = np.zeros((len(refs), len(preds)))
        for i, a in enumerate(refs):
            for j, b in enumerate(preds):
                if edge(a, b):
                    ov = sum(_overlap(x, y) for x in _all_spans(a) for y in _all_spans(b))
                    tot = sum(e - s for s, e in _all_spans(a)) + sum(e - s for s, e in _all_spans(b))
                    m[i, j] = 1.0 + 0.001 * (ov / tot if tot else 0.0)
        r, c = linear_sum_assignment(-m)
        return [(refs[i]["local_ref"], preds[j]["local_ref"]) for i, j in zip(r, c) if m[i, j] > 0]

    def claims(self):
        rc, pc = list(self.ua.ref_claims.values()), list(self.ua.pred_claims.values())
        core_edges = {(a["local_ref"], b["local_ref"]) for a in rc for b in pc if self.core(a, b)}
        self.ua.matches["core"] = self._match(rc, pc, lambda a, b: (a["local_ref"], b["local_ref"]) in core_edges)
        core_map = dict(self.ua.matches["core"])
        fails = {e: self.full_failures(self.ua.ref_claims[e[0]], self.ua.pred_claims[e[1]], core_map) for e in core_edges}
        full_edges = {e for e, f in fails.items() if not f}
        self.ua.matches["full"] = self._match(rc, pc, lambda a, b: (a["local_ref"], b["local_ref"]) in full_edges)
        ev_edges = {e for e in full_edges if self.evidence_ok(self.ua.ref_claims[e[0]], self.ua.pred_claims[e[1]])}
        self.ua.matches["evidence"] = self._match(rc, pc, lambda a, b: (a["local_ref"], b["local_ref"]) in ev_edges)
        for e in self.ua.matches["core"]:
            self.ua.field_failures[e] = fails[e]
            self.ua.diagnostics[e] = self.diagnose(self.ua.ref_claims[e[0]], self.ua.pred_claims[e[1]], core_map)

    # ------------------------------------------------------------------ diagnostics

    def _formula_pairs(self, a, b):
        oa, ob = a.get("object") or {}, b.get("object") or {}
        if oa.get("t") in ("formula", "set") and ob.get("t") == oa.get("t"):
            yield "object", oa, ob
        qa, qb = a.get("qualifiers") or {}, b.get("qualifiers") or {}
        for name in sorted(set(qa) & set(qb)):
            q = self.lk.qualifier(name)
            if not q:
                continue
            kind, rng = q
            if kind == "map" and isinstance(qa[name], dict) and isinstance(qb[name], dict):
                vk = self.lk.map_value_kind(rng)
                if vk in ("formula", "set"):
                    for k in sorted(set(qa[name]) & set(qb[name])):
                        yield f"{name}.{k}", as_formula(qa[name][k], vk), as_formula(qb[name][k], vk)
            elif kind in ("formula", "set"):
                yield name, as_formula(qa[name], kind), as_formula(qb[name], kind)

    def diagnose(self, a, b, core_map) -> list[str]:
        out = []
        for where, fa, fb in self._formula_pairs(a, b):
            sb = {canonical_symbol(k): v for k, v in (fb.get("symbols") or {}).items()}
            for sym, ba in (fa.get("symbols") or {}).items():
                key = canonical_symbol(sym)
                bb = sb.get(key)
                ok = bb is not None and ba.get("bind") == bb.get("bind")
                if ok and ba.get("bind") in ("variable", "family_param"):
                    ok = self.ref_eq(ba.get("entity"), bb.get("entity"))
                elif ok and ba.get("bind") in ("param_of", "param_expr_of"):
                    ok = core_map.get(ba.get("claim")) == bb.get("claim") and ba.get("param") == bb.get("param")
                self.ua.bindings.append({"ref_claim": a["local_ref"], "pred_claim": b["local_ref"], "where": where,
                                         "symbol": key, "ref_bind": ba.get("bind"), "pred_bind": bb.get("bind") if bb else None, "correct": ok})
                if not ok and "bindings" not in out:
                    out.append("bindings")
        for r in (a.get("subject"), ref_of(a.get("object") or {})):
            ea = self.ua.ref_entities.get(r)
            if ea and ea.get("scope") == "local" and r in self.emap:
                eb = self.ua.pred_entities.get(self.emap[r])
                if eb and ea.get("scope_segment") != eb.get("scope_segment") and "extent" not in out:
                    out.append("extent")
        return out

    def scopes(self):
        for p in self.ua.entity_pairs:
            ea, eb = self.ua.ref_entities.get(p.ref), self.ua.pred_entities.get(p.pred)
            if ea and eb and ea.get("scope") == "local":
                self.ua.scopes.append({"ref": p.ref, "pred": p.pred, "ref_segment": ea.get("scope_segment"),
                                       "pred_segment": eb.get("scope_segment"), "ref_extent": ea.get("extent"),
                                       "pred_extent": eb.get("extent"),
                                       "correct": ea.get("scope_segment") == eb.get("scope_segment")})

    def alternatives(self):
        core = dict(self.ua.matches["core"])
        inv = {v: k for k, v in core.items()}
        rg = [a["refs"] for a in self.r.batch.get("alternatives", [])]
        pg = [a["refs"] for a in self.p.batch.get("alternatives", [])]

        def outcome(group, mapping, others):
            mapped = {mapping.get(x) for x in group}
            if None not in mapped and any(set(o) == mapped for o in others):
                return "matched"
            if mapped - {None}:
                return "ambiguity_collapsed"
            return "unmatched"

        self.ua.alternatives_ref = [(g, outcome(g, core, pg)) for g in rg]
        self.ua.alternatives_pred = [(g, outcome(g, inv, rg)) for g in pg]

    def unsupported(self):
        ru, pu = self.r.batch.get("unsupported", []), self.p.batch.get("unsupported", [])
        self.ua.unsupported_n = (len(ru), len(pu))
        if not ru or not pu:
            return
        m = np.array([[float(_overlap((a["start"], a["end"]), (b["start"], b["end"]))) for b in pu] for a in ru])
        r, c = linear_sum_assignment(-m)
        self.ua.unsupported_pairs = [(ru[i]["local_ref"], pu[j]["local_ref"]) for i, j in zip(r, c) if m[i, j] > 0]

    def run(self) -> UnitAlignment:
        self.entities()
        self.claims()
        self.scopes()
        self.alternatives()
        self.unsupported()
        return self.ua


def align_unit(ref: Side, pred: Side, lookup: SchemaLookup | None = None,
               comparator: ValueComparator | None = None) -> UnitAlignment:
    """Align ``pred`` to ``ref`` (both stored-form batches of the same unit)."""
    from .validate import default_lookup

    return _Aligner(ref, pred, lookup or default_lookup(), comparator or ValueComparator()).run()


def describe(ua: UnitAlignment) -> str:
    """Human-readable alignment, for comparison with a hand alignment (instruments §9)."""
    lines = [f"# unit {ua.unit}", "entities:"]
    for p in ua.entity_pairs:
        lines.append(f"  {p.ref} = {p.pred}  ({p.sim:.2f} {p.basis})")
    lines.append(f"  ref only: {ua.entity_unmatched_ref}  pred only: {ua.entity_unmatched_pred}")
    if ua.identity_near_misses:
        lines.append(f"  identity near misses: {ua.identity_near_misses}")
    for t in TIERS:
        lines.append(f"{t}: {sorted(ua.matches.get(t, []))}")
    for e, f in sorted(ua.field_failures.items()):
        if f or ua.diagnostics.get(e):
            lines.append(f"  {e[0]}~{e[1]} full-tier failures {f} diagnostics {ua.diagnostics.get(e)}")
    lines.append(f"alternatives ref: {ua.alternatives_ref} pred: {ua.alternatives_pred}")
    lines.append(f"unsupported: {ua.unsupported_pairs} of {ua.unsupported_n}")
    return "\n".join(lines)
