"""Batch validation by category (instruments §2.3; D4 §4.3 step 3; D1 §11).

Never stops at the first error: the top level and every item are validated separately with
Pydantic, and semantic checks run on every item that parsed. Categories:

- ``malformed``: Pydantic errors (stable ``type`` and location), binding fields missing for
  their kind, a stored span or phrase without offsets.
- ``unknown_schema_element`` (INV-03): predicate, class, qualifier, identity slot or enum
  value (statement kind, statement role, modality, polarity, scope extent, bind kind,
  condition predicate, enum object) not in v0.
- ``type_mismatch``: subject or object class outside domain or range (``class_ancestors``),
  value type other than the predicate's ``ci:object``, a schema qualifier the predicate does
  not list, entity scope disagreeing with the class's ``ci:scope``, a class's identity
  attributes missing, condition-predicate arity or argument class.
- ``reference_error``: duplicate or unresolved local ref, a ref of the wrong kind (including
  a symbol binding that names the wrong kind of local ref), a condition ``claim`` node outside
  the batch (INV-08), a reference cycle among conditions (D5 §5.2), unknown sentence ids.
- ``invariant``: INV-01, INV-02, INV-05, INV-06, INV-10.

INV-09 cannot be violated by a batch (a batch has no "unconditional" flag); the validator
instead *marks* every claim with a ``phrase``/``unsupported`` condition leaf as conditional
(``ValidationReport.conditional_claims``), which consumers must honour.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Iterable

from pydantic import ValidationError

from .batch import (
    CONDITION_ADAPTER,
    ENTITY_ARG_ADAPTER,
    ITEM_MODELS,
    STR_ADAPTER,
    VALUE_ADAPTER,
    BatchShell,
    as_formula,
    ref_of,
)
from .conditions import as_dict, claim_refs, entity_positions, formula_positions, has_uninterpreted, iter_nodes
from .schema_lookup import CORE_QUALIFIERS, OBJECT_T, SchemaLookup

CATEGORIES = ("malformed", "unknown_schema_element", "type_mismatch", "reference_error", "invariant")
SECTIONS = ("entities", "statements", "claims", "alternatives", "unsupported")
_KIND_OF_SECTION = {"entities": "entity", "statements": "statement", "claims": "claim", "unsupported": "unsupported"}


@dataclass
class Issue:
    category: str
    code: str
    loc: tuple
    message: str
    ref: str | None = None


@dataclass
class ValidationReport:
    form: str
    issues: list[Issue] = field(default_factory=list)
    conditional_claims: list[str] = field(default_factory=list)  # INV-09 marks

    @property
    def ok(self) -> bool:
        return not self.issues

    def categories(self) -> set[str]:
        return {i.category for i in self.issues}

    def codes(self) -> set[str]:
        return {i.code for i in self.issues}

    def counts(self) -> dict[str, int]:
        out = dict.fromkeys(CATEGORIES, 0)
        for i in self.issues:
            out[i.category] += 1
        return out

    def lines(self) -> list[str]:
        return [f"{i.category}\t{i.code}\t{'.'.join(map(str, i.loc))}\t{i.message}" for i in self.issues]


_LOOKUP: SchemaLookup | None = None


def default_lookup() -> SchemaLookup:
    global _LOOKUP
    if _LOOKUP is None:
        _LOOKUP = SchemaLookup()
    return _LOOKUP


class _V:
    def __init__(self, raw, lookup, form, canonical_text, sentence_ids, unit_ranges):
        self.raw = raw
        self.lk = lookup
        self.form = form
        self.text = canonical_text
        self.sids = set(sentence_ids) if sentence_ids is not None else None
        self.unit_ranges = list(unit_ranges) if unit_ranges else None
        self.rep = ValidationReport(form)
        self.refs: dict[str, tuple[str, int]] = {}
        self.etype: dict[str, str] = {}
        self.escope: dict[str, str] = {}
        self.parsed: dict[str, list] = {s: [] for s in SECTIONS}
        self.claim_raw: dict[str, dict] = {}

    def add(self, cat, code, loc, msg, ref=None):
        self.rep.issues.append(Issue(cat, code, tuple(loc), msg, ref))

    def pyd(self, err: ValidationError, prefix):
        for e in err.errors():
            self.add("malformed", e["type"], (*prefix, *e["loc"]), e["msg"])

    # ------------------------------------------------------------------ structure

    def structure(self):
        raw = self.raw
        if not isinstance(raw, dict):
            self.add("malformed", "not_an_object", (), "batch is not a JSON object")
            return False
        try:
            BatchShell.model_validate(raw)
        except ValidationError as e:
            self.pyd(e, ())
        for sec in SECTIONS:
            items = raw.get(sec, [])
            if not isinstance(items, list):
                continue
            model = ITEM_MODELS[self.form][sec]
            for i, item in enumerate(items):
                loc = (sec, i)
                lref = item.get("local_ref") if isinstance(item, dict) else None
                inv02 = False
                if sec == "claims" and isinstance(item, dict):
                    obj = item.get("object")
                    if obj is None:
                        self.add("invariant", "INV-02", (*loc, "object"), "claim has no object", lref)
                        inv02 = True
                    elif isinstance(obj, dict) and "ref" in obj and obj.get("t") not in (None, "entity"):
                        self.add("invariant", "INV-02", (*loc, "object"),
                                 "object is both an entity ref and a value", lref)
                        inv02 = True
                try:
                    p = model.model_validate(item)
                    self.parsed[sec].append((i, p))
                except ValidationError as e:
                    for er in e.errors():
                        if inv02 and er["loc"][:1] == ("object",):
                            continue
                        self.add("malformed", er["type"], (*loc, *er["loc"]), er["msg"], lref)
                if isinstance(lref, str) and sec in _KIND_OF_SECTION:
                    if lref in self.refs:
                        self.add("reference_error", "duplicate_local_ref", (*loc, "local_ref"),
                                 f"local ref {lref!r} already used by {self.refs[lref][0]}", lref)
                    else:
                        self.refs[lref] = (_KIND_OF_SECTION[sec], i)
                        if sec == "entities" and isinstance(item.get("type"), str):
                            self.etype[lref] = self.lk.bare(item["type"])
                            self.escope[lref] = item.get("scope")
                        elif sec == "statements":
                            self.etype[lref] = "Statement"
                            self.escope[lref] = "local"
                        elif sec == "claims":
                            self.claim_raw[lref] = item
        return True

    # ------------------------------------------------------------------ helpers

    def kind(self, r):
        return self.refs.get(r, (None,))[0]

    def need(self, r, kinds, loc, what, code="wrong_ref_kind", owner=None) -> bool:
        k = self.kind(r)
        if k is None:
            self.add("reference_error", "unresolved_ref", loc, f"{what} {r!r} does not resolve", owner)
            return False
        if k not in kinds:
            self.add("reference_error", code, loc, f"{what} {r!r} is a {k}, expected {'/'.join(kinds)}", owner)
            return False
        return True

    def check_sentence(self, sid, loc, owner):
        if self.sids is not None and sid is not None and sid not in self.sids:
            self.add("reference_error", "unknown_sentence", loc, f"sentence id {sid!r} not in the packet", owner)

    def check_span(self, start, end, loc, owner, text=None, coarse=False):
        if start is None or end is None:
            self.add("malformed", "span_missing", loc, "stored span without start/end", owner)
            return
        if self.text is not None:
            if not (0 <= start < end <= len(self.text)):
                self.add("invariant", "INV-10", loc, f"span ({start}, {end}) outside canonical text", owner)
                return
            if text is not None and not coarse and self.text[start:end] != text:
                self.add("invariant", "INV-10", loc, "span text differs from canonical substring", owner)
        if self.unit_ranges and not any(s <= start and end <= e for s, e in self.unit_ranges):
            self.add("invariant", "span_outside_unit", loc, f"span ({start}, {end}) outside the unit", owner)

    def check_enum(self, enum, v, loc, owner, what):
        if v is None:
            return
        if v not in self.lk.enum_values(enum):
            self.add("unknown_schema_element", f"unknown_{what}", loc, f"{what} {v!r} not in {enum}", owner)

    def check_bindings(self, value: dict, loc, owner):
        for sym, b in (value.get("symbols") or {}).items():
            b = as_dict(b)
            bl = (*loc, "symbols", sym)
            kind = b.get("bind")
            if kind not in self.lk.enum_values("BindKind"):
                self.add("unknown_schema_element", "unknown_bind_kind", bl, f"bind {kind!r} not in BindKind", owner)
                continue
            if kind in ("variable", "family_param"):
                if not b.get("entity"):
                    self.add("malformed", "binding_fields", bl, f"{kind} binding needs 'entity'", owner)
                    continue
                if b.get("claim"):
                    self.add("malformed", "binding_fields", bl, f"{kind} binding has 'claim'", owner)
                r = b["entity"]
                k = self.kind(r)
                if k is None:
                    self.add("reference_error", "unresolved_ref", bl, f"binding entity {r!r} does not resolve", owner)
                elif k != "entity":
                    self.add("reference_error", "binding_wrong_ref_kind", bl,
                             f"{kind} binding names {r!r}, a {k}; expected an entity local ref", owner)
                elif kind == "variable" and self.escope.get(r) != "local":
                    self.add("reference_error", "binding_wrong_ref_kind", bl,
                             f"variable binding names {r!r}, a {self.escope.get(r)} {self.etype.get(r)}; expected a local entity", owner)
                elif kind == "family_param" and not self.lk.is_a(self.etype.get(r, ""), "FamilyParameter"):
                    self.add("reference_error", "binding_wrong_ref_kind", bl,
                             f"family_param binding names {r!r}, a {self.etype.get(r)}; expected a FamilyParameter", owner)
            elif kind in ("param_of", "param_expr_of"):
                if not b.get("claim") or not b.get("param"):
                    self.add("malformed", "binding_fields", bl, f"{kind} binding needs 'claim' and 'param'", owner)
                    continue
                if b.get("entity"):
                    self.add("malformed", "binding_fields", bl, f"{kind} binding has 'entity'", owner)
                r = b["claim"]
                k = self.kind(r)
                if k is None:
                    self.add("reference_error", "unresolved_ref", bl, f"binding claim {r!r} does not resolve", owner)
                elif k != "claim":
                    self.add("reference_error", "binding_wrong_ref_kind", bl,
                             f"{kind} binding names {r!r}, a {k}; expected a claim local ref", owner)
                else:
                    pv = (self.claim_raw.get(r, {}).get("qualifiers") or {}).get("param_values")
                    if not isinstance(pv, dict) or b["param"] not in pv:
                        self.add("reference_error", "binding_param_missing", bl,
                                 f"claim {r!r} has no param_values entry {b['param']!r}", owner)
            elif any(b.get(f) for f in ("entity", "claim", "param")):
                self.add("malformed", "binding_fields", bl, f"{kind} binding takes no target", owner)

    def check_tree(self, tree: dict, loc, owner):
        for f_kind, fv in formula_positions(tree):
            self.check_bindings(fv, loc, owner)
        for n in iter_nodes(tree):
            op = n.get("op")
            if op == "claim":
                if self.kind(n["ref"]) != "claim":
                    self.add("reference_error", "INV-08", loc,
                             f"condition claim node {n['ref']!r} is not a claim of this batch", owner)
            elif op == "pred":
                cp = self.lk.condition_predicate(n["name"])
                if cp is None:
                    self.add("unknown_schema_element", "unknown_condition_predicate", loc,
                             f"condition predicate {n['name']!r} not in ConditionPredicate", owner)
                    continue
                arity, nargs = str(cp.get("ci:arity", "")), len(n.get("args", []))
                if (arity == "2+" and nargs < 2) or (arity.isdigit() and nargs != int(arity)):
                    self.add("type_mismatch", "condition_arity", loc, f"{n['name']} takes {arity} args, got {nargs}", owner)
                cls = cp.get("ci:args")
                for r in entity_positions({"op": "pred", "name": n["name"], "args": n.get("args", [])}):
                    if self.need(r, ("entity",), loc, "condition argument", owner=owner) and cls and not self.lk.is_a(self.etype.get(r, ""), cls):
                        self.add("type_mismatch", "condition_arg_class", loc, f"{r!r} is a {self.etype.get(r)}, expected {cls}", owner)
            elif op in ("phrase", "unsupported"):
                if self.form == "model":
                    self.check_sentence(n.get("sentence"), loc, owner)
                else:
                    self.check_span(n.get("start"), n.get("end"), loc, owner, n.get("text"), bool(n.get("coarse")))

    # ------------------------------------------------------------------ items

    def entities(self):
        for i, e in self.parsed["entities"]:
            loc, r = ("entities", i), e.local_ref
            t = self.lk.bare(e.type)
            if not self.lk.is_entity_class(t):
                self.add("unknown_schema_element", "unknown_class", (*loc, "type"), f"class {e.type!r} not an entity class of v0", r)
                continue
            cs = self.lk.class_scope(t)
            if cs and cs != e.scope:
                self.add("type_mismatch", "scope_disagrees_with_class", (*loc, "scope"), f"{t} is {cs} (ci:scope), entity says {e.scope}", r)
            seg = getattr(e, "scope_segment", None)
            if e.scope == "local":
                if self.form == "model" and e.extent is None:
                    self.add("invariant", "INV-05", (*loc, "extent"), "local entity without extent", r)
                if self.form == "stored" and not seg:
                    self.add("invariant", "INV-05", (*loc, "scope_segment"), "local entity without scope segment", r)
            else:
                if e.extent is not None or seg:
                    self.add("invariant", "INV-05", (*loc, "extent"), "global entity with an extent or scope segment", r)
            keys = self.lk.identity_keys(t)
            for slot, val in e.identity.items():
                if slot not in keys:
                    self.add("unknown_schema_element", "unknown_identity_slot", (*loc, "identity", slot), f"{slot!r} is not an identity key of {t}", r)
                    continue
                rng = self.lk.sv.induced_slot(slot).range
                if rng and self.lk.sv.get_class(rng) is not None:
                    vr = ref_of(val)
                    if vr is None:
                        self.add("malformed", "identity_ref", (*loc, "identity", slot), f"{slot} must name a local ref", r)
                    elif self.need(vr, ("entity", "statement"), (*loc, "identity", slot), f"identity {slot}", owner=r):
                        if not self.lk.is_a(self.etype.get(vr, ""), rng):
                            self.add("type_mismatch", "identity_class", (*loc, "identity", slot), f"{vr!r} is not a {rng}", r)
            missing = [k for k in keys if k not in e.identity]
            if missing:
                self.add("type_mismatch", "identity_keys_missing", (*loc, "identity"), f"{t} identity needs {missing}", r)

    def statements(self):
        for i, s in self.parsed["statements"]:
            loc = ("statements", i)
            self.check_enum("StatementKind", s.kind, (*loc, "kind"), s.local_ref, "statement_kind")
            if self.form == "model" and isinstance(s.anchor, list):
                for sid in s.anchor:
                    self.check_sentence(sid, (*loc, "anchor"), s.local_ref)
            if isinstance(s.anchor, list) and not s.anchor:
                self.add("malformed", "anchor_empty", (*loc, "anchor"), "statement anchor is empty", s.local_ref)

    def qualifier(self, name, val, rule, loc, owner, formulas: list, trees: list):
        lk = self.lk
        q = lk.qualifier(name)
        if q is None:
            self.add("unknown_schema_element", "unknown_qualifier", loc, f"qualifier {name!r} not in v0", owner)
            return
        bare = lk.bare(name)
        if bare not in CORE_QUALIFIERS and (rule is None or bare not in rule.qualifiers):
            self.add("type_mismatch", "qualifier_not_allowed", loc, f"{bare!r} is not a qualifier of {rule.name if rule else '?'}", owner)
        kind, rng = q
        try:
            if kind == "enum":
                if bare == "scope" and self.form == "stored":
                    if not isinstance(val, dict) or set(val) - {"extent", "segment"} or "extent" not in val:
                        self.add("malformed", "scope_stored", loc, "stored scope is {extent, segment}", owner)
                        return
                    self.check_enum(rng, val["extent"], loc, owner, bare)
                    if not val.get("segment"):
                        self.add("malformed", "scope_segment_missing", loc, "stored scope without segment", owner)
                    return
                self.check_enum(rng, STR_ADAPTER.validate_python(val), loc, owner, bare)
            elif kind == "condition":
                tree = CONDITION_ADAPTER.validate_python(val).model_dump(exclude_none=True)
                trees.append(tree)
            elif kind == "entity":
                r = ref_of(ENTITY_ARG_ADAPTER.validate_python(val))
                if self.need(r, ("entity", "statement"), loc, f"qualifier {bare}", owner=owner) and rng and lk.sv.get_class(rng) and not lk.is_a(self.etype.get(r, ""), rng):
                    self.add("type_mismatch", "qualifier_class", loc, f"{r!r} is a {self.etype.get(r)}, expected {rng}", owner)
            elif kind == "map":
                if not isinstance(val, dict):
                    self.add("malformed", "map_expected", loc, f"{bare} must be an object of key -> value", owner)
                    return
                vk = lk.map_value_kind(rng)
                for k, v in val.items():
                    if vk in ("formula", "set"):
                        fv = VALUE_ADAPTER.validate_python(as_formula(v, vk)).model_dump(exclude_none=True)
                        if fv["t"] != vk:
                            self.add("type_mismatch", "value_type", (*loc, k), f"{bare}[{k}] must be a {vk}", owner)
                        formulas.append(((*loc, k), fv))
                    else:
                        STR_ADAPTER.validate_python(v)
            else:
                v = val
                if kind in ("formula", "set") and isinstance(val, str):
                    v = as_formula(val, kind)
                if kind == "phrase" and isinstance(val, str):
                    v = {"t": "phrase", "text": val}
                pv = VALUE_ADAPTER.validate_python(v).model_dump(exclude_none=True)
                if pv["t"] not in OBJECT_T.get(kind, {kind}):
                    self.add("type_mismatch", "value_type", loc, f"{bare} must be a {kind}, got {pv['t']}", owner)
                if pv["t"] in ("formula", "set"):
                    formulas.append((loc, pv))
                if pv["t"] == "phrase" and self.form == "stored":
                    self.check_span(pv.get("start"), pv.get("end"), loc, owner, pv.get("text"), bool(pv.get("coarse")))
        except ValidationError as e:
            for er in e.errors():
                self.add("malformed", er["type"], (*loc, *er["loc"]), er["msg"], owner)

    def claims(self):
        lk = self.lk
        referenced: set[str] = set()
        cond_edges: dict[str, set[str]] = {}
        for i, c in self.parsed["claims"]:
            loc, r = ("claims", i), c.local_ref
            rule = lk.predicate(c.predicate)
            if rule is None:
                self.add("unknown_schema_element", "unknown_predicate", (*loc, "predicate"), f"predicate {c.predicate!r} not in v0", r)
            # subject
            if self.need(c.subject, ("entity", "statement"), (*loc, "subject"), "subject", owner=r) and rule and rule.domain:
                st = self.etype.get(c.subject, "")
                if not lk.is_a(st, rule.domain):
                    self.add("type_mismatch", "subject_class", (*loc, "subject"), f"subject {c.subject!r} is a {st}, {rule.name} needs {rule.domain}", r)
            # object
            obj = c.object.model_dump(exclude_none=True)
            formulas: list = []
            trees: list = []
            oref = ref_of(obj)
            if oref is not None:
                if rule and rule.object_kind != "entity":
                    self.add("type_mismatch", "object_kind", (*loc, "object"), f"{rule.name} takes a {rule.object_kind} object, got an entity ref", r)
                elif self.need(oref, ("entity", "statement"), (*loc, "object"), "object", owner=r) and rule and rule.range:
                    ot = self.etype.get(oref, "")
                    if not lk.is_a(ot, rule.range):
                        self.add("type_mismatch", "object_class", (*loc, "object"), f"object {oref!r} is a {ot}, {rule.name} needs {rule.range}", r)
            else:
                t = obj.get("t")
                if rule and t not in OBJECT_T.get(rule.object_kind, set()):
                    self.add("type_mismatch", "object_kind", (*loc, "object"), f"{rule.name} takes a {rule.object_kind} object, got {t}", r)
                if t == "enum":
                    if rule and rule.range and obj["enum"] != rule.range:
                        self.add("type_mismatch", "enum_name", (*loc, "object"), f"enum {obj['enum']!r}, expected {rule.range}", r)
                    if not lk.has_enum(obj["enum"]):
                        self.add("unknown_schema_element", "unknown_enum", (*loc, "object"), f"enum {obj['enum']!r} not in v0", r)
                    else:
                        self.check_enum(obj["enum"], obj["v"], (*loc, "object"), r, "enum_value")
                if t in ("formula", "set"):
                    formulas.append(((*loc, "object"), obj))
                if t == "phrase" and self.form == "stored":
                    self.check_span(obj.get("start"), obj.get("end"), (*loc, "object"), r, obj.get("text"), bool(obj.get("coarse")))
            # statement
            if c.statement is not None:
                self.need(c.statement, ("statement",), (*loc, "statement"), "statement", owner=r)
            self.check_enum("StatementRole", c.statement_role, (*loc, "statement_role"), r, "statement_role")
            # qualifiers
            for name, val in c.qualifiers.items():
                self.qualifier(name, val, rule, (*loc, "qualifiers", name), r, formulas, trees)
            for floc, fv in formulas:
                self.check_bindings(fv, floc, r)
            for tree in trees:
                self.check_tree(tree, (*loc, "qualifiers"), r)
                for cr in claim_refs(tree):
                    referenced.add(cr)
                    cond_edges.setdefault(r, set()).add(cr)
                if has_uninterpreted(tree) and r not in self.rep.conditional_claims:
                    self.rep.conditional_claims.append(r)
            # evidence
            if not any(ev.role == "primary" for ev in c.evidence):
                self.add("invariant", "INV-01", (*loc, "evidence"), "stated claim without primary evidence", r)
            for k, ev in enumerate(c.evidence):
                if self.form == "model":
                    self.check_sentence(ev.sentence, (*loc, "evidence", k), r)
                else:
                    self.check_span(ev.start, ev.end, (*loc, "evidence", k), r)
        # INV-06
        for i, c in self.parsed["claims"]:
            if c.qualifiers.get("modality") == "supposed" and c.local_ref not in referenced and "scope" not in c.qualifiers:
                self.add("invariant", "INV-06", ("claims", i), "supposed claim neither referenced by a condition nor scoped", c.local_ref)
        # cycles (D5 §5.2)
        state: dict[str, int] = {}
        in_cycle: set[str] = set()

        def dfs(u, path):
            state[u] = 1
            path.append(u)
            for v in sorted(cond_edges.get(u, ())):
                if state.get(v) == 1:
                    in_cycle.update(path[path.index(v):])
                elif state.get(v) is None:
                    dfs(v, path)
            path.pop()
            state[u] = 2

        for u in sorted(cond_edges):
            if state.get(u) is None:
                dfs(u, [])
        for u in sorted(in_cycle):
            self.add("reference_error", "condition_cycle", ("claims", self.refs.get(u, ("", "?"))[1]), f"claim {u!r} is on a condition reference cycle", u)

    def rest(self):
        for i, a in self.parsed["alternatives"]:
            for k, r in enumerate(a.refs):
                self.need(r, ("claim",), ("alternatives", i, "refs", k), "alternative member")
        for i, u in self.parsed["unsupported"]:
            loc = ("unsupported", i)
            if self.form == "model":
                self.check_sentence(u.sentence, (*loc, "sentence"), u.local_ref)
            else:
                self.check_span(u.start, u.end, loc, u.local_ref)

    def run(self) -> ValidationReport:
        if self.structure():
            self.entities()
            self.statements()
            self.claims()
            self.rest()
        return self.rep


def validate_batch(
    raw: Any,
    lookup: SchemaLookup | None = None,
    form: str = "model",
    *,
    canonical_text: str | None = None,
    sentence_ids: Iterable[str] | None = None,
    unit_ranges: Iterable[tuple[int, int]] | None = None,
) -> ValidationReport:
    """Validate a raw batch dict (model-facing ``form="model"`` or ``"stored"``).

    ``sentence_ids`` (model form) enables the unknown-sentence check; ``canonical_text`` and
    ``unit_ranges`` (stored form) enable INV-10 and the inside-the-unit check.
    """
    return _V(raw, lookup or default_lookup(), form, canonical_text, sentence_ids, unit_ranges).run()
