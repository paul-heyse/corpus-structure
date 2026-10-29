"""Batch conformance, reference and type checks (P0-S-2; schema and rules §3.7).

`check_batch(batch_json, compiled, form, *, sentence_ids, canonical_text, unit_ranges)` judges a
batch in the model-facing (`"model"`) or stored (`"stored"`) form against one compiled schema
version. It ports the spike validator (`code/instruments/validate.py`) without its grammar calls:
the slot-kind check is `core.value_kind_matches_slot` at finalize, and the bare-unit check waits
for M12 (P0CL-14).

**It never stops at the first error.** The envelope and every item are validated separately with
the compiled per-predicate models on the JSON path (strict), and the semantic checks run on every
item that parsed. Each issue has a category, a typed code, a path, a message projected from the
code, and the local ref of its item.

**Categories** (D1 INV-03, D4 §4.3 step 5):
- `malformed`: a Pydantic error, by its stable error type (`missing`, `extra_forbidden`, …), and
  binding fields wrong for their kind (`binding_fields`);
- `unknown_schema_element`: a Pydantic error at a schema-owned position (the predicate tag, an
  entity class, a statement kind, a qualifier name, a modality, polarity or scope extent, a
  statement role, a bind kind, an enum name or value), at the same path, and an unknown identity
  slot or condition predicate;
- `type_mismatch`: subject, object and entity-qualifier classes against domain and range by
  `is_a`, an entity reference where a value belongs and the reverse, a schema qualifier the
  predicate does not list, entity scope against `ci:scope`, missing identity slots, and
  condition-predicate arity and argument class;
- `reference_error`: duplicate, unresolved and wrong-kind local refs, each position checked
  against the kinds it may name; binding targets; a `claim` condition node naming no claim of
  the batch (INV-08); condition cycles; sentence ids against the frame; an `outside` item whose
  citing sentence the frame does not list (`uncited_reference`) or whose link target is not a D1
  §3.4 locator or an author link target;
- `invariant`: INV-01, INV-02, INV-05, INV-06 (a `supposed` claim no condition references and
  with no scope) and INV-10 (stored spans against the canonical text and inside the unit).

An `ExternalReference` (an `outside` item) is an entity. It may stand as subject or object where a
statement is expected, as a `claim` condition target and as a binding's claim (D1 §4.4).

**The report** yields the rejected items in the `claim_proposal` payload's `rejected` form, so
metrics count them (D3 §6.2).
"""

from __future__ import annotations

import json
import typing
from collections.abc import Iterable, Iterator, Mapping, Sequence
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any, TypeGuard

from pydantic import TypeAdapter, ValidationError, create_model
from pydantic_core import ErrorDetails

from corpus_structure.core import batch as B
from corpus_structure.core import locators
from corpus_structure.core import values as V
from corpus_structure.core.payloads import RejectedItem
from corpus_structure.core.values import refuse_m11_fields

if typing.TYPE_CHECKING:
    from corpus_structure.schema.compile import CompiledSchema

FORMS = ("model", "stored")
SECTIONS:tuple[str,...] = ("entities", "statements", "claims", "alternatives", "unsupported")
CORE = "core:"


class IssueCategory(StrEnum):
    MALFORMED = "malformed"
    UNKNOWN_SCHEMA_ELEMENT = "unknown_schema_element"
    TYPE_MISMATCH = "type_mismatch"
    REFERENCE_ERROR = "reference_error"
    INVARIANT = "invariant"


class IssueCode(StrEnum):
    """The checks' own codes; a Pydantic error keeps its stable error type as its code."""

    NOT_JSON = "not_json"
    NOT_AN_OBJECT = "not_an_object"
    BINDING_FIELDS = "binding_fields"
    M11_FIELDS = "m11_fields"
    UNKNOWN_PREDICATE = "unknown_predicate"
    UNKNOWN_CLASS = "unknown_class"
    UNKNOWN_STATEMENT_KIND = "unknown_statement_kind"
    UNKNOWN_QUALIFIER = "unknown_qualifier"
    UNKNOWN_MODALITY = "unknown_modality"
    UNKNOWN_POLARITY = "unknown_polarity"
    UNKNOWN_SCOPE_EXTENT = "unknown_scope_extent"
    UNKNOWN_STATEMENT_ROLE = "unknown_statement_role"
    UNKNOWN_BIND_KIND = "unknown_bind_kind"
    UNKNOWN_ENUM = "unknown_enum"
    UNKNOWN_ENUM_VALUE = "unknown_enum_value"
    UNKNOWN_IDENTITY_SLOT = "unknown_identity_slot"
    UNKNOWN_CONDITION_PREDICATE = "unknown_condition_predicate"
    SUBJECT_CLASS = "subject_class"
    OBJECT_CLASS = "object_class"
    OBJECT_KIND = "object_kind"
    ENUM_NAME = "enum_name"
    QUALIFIER_NOT_ALLOWED = "qualifier_not_allowed"
    QUALIFIER_CLASS = "qualifier_class"
    SCOPE_DISAGREES_WITH_CLASS = "scope_disagrees_with_class"
    IDENTITY_KEYS_MISSING = "identity_keys_missing"
    CONDITION_ARITY = "condition_arity"
    CONDITION_ARG_CLASS = "condition_arg_class"
    DUPLICATE_LOCAL_REF = "duplicate_local_ref"
    UNRESOLVED_REF = "unresolved_ref"
    WRONG_REF_KIND = "wrong_ref_kind"
    BINDING_WRONG_REF_KIND = "binding_wrong_ref_kind"
    BINDING_PARAM_MISSING = "binding_param_missing"
    CONDITION_CLAIM_OUTSIDE_BATCH = "INV-08"
    CONDITION_CYCLE = "condition_cycle"
    UNKNOWN_SENTENCE = "unknown_sentence"
    UNCITED_REFERENCE = "uncited_reference"
    BAD_REFERENCE_TARGET = "bad_reference_target"
    INV_01 = "INV-01"
    INV_02 = "INV-02"
    INV_05 = "INV-05"
    INV_06 = "INV-06"
    INV_10 = "INV-10"
    SPAN_OUTSIDE_UNIT = "span_outside_unit"


_C, _K = IssueCategory, IssueCode
CATEGORY: Mapping[IssueCode, IssueCategory] = {
    _K.NOT_JSON: _C.MALFORMED,
    _K.NOT_AN_OBJECT: _C.MALFORMED,
    _K.BINDING_FIELDS: _C.MALFORMED,
    _K.M11_FIELDS: _C.MALFORMED,
    **{
        c: _C.UNKNOWN_SCHEMA_ELEMENT
        for c in _K
        if c.value.startswith("unknown_") and c is not _K.UNKNOWN_SENTENCE
    },
    **{
        c: _C.TYPE_MISMATCH
        for c in (
            _K.SUBJECT_CLASS,
            _K.OBJECT_CLASS,
            _K.OBJECT_KIND,
            _K.ENUM_NAME,
            _K.QUALIFIER_NOT_ALLOWED,
            _K.QUALIFIER_CLASS,
            _K.SCOPE_DISAGREES_WITH_CLASS,
            _K.IDENTITY_KEYS_MISSING,
            _K.CONDITION_ARITY,
            _K.CONDITION_ARG_CLASS,
        )
    },
    **{
        c: _C.REFERENCE_ERROR
        for c in (
            _K.DUPLICATE_LOCAL_REF,
            _K.UNRESOLVED_REF,
            _K.WRONG_REF_KIND,
            _K.BINDING_WRONG_REF_KIND,
            _K.BINDING_PARAM_MISSING,
            _K.CONDITION_CLAIM_OUTSIDE_BATCH,
            _K.CONDITION_CYCLE,
            _K.UNKNOWN_SENTENCE,
            _K.UNCITED_REFERENCE,
            _K.BAD_REFERENCE_TARGET,
        )
    },
    **{
        c: _C.INVARIANT
        for c in (_K.INV_01, _K.INV_02, _K.INV_05, _K.INV_06, _K.INV_10, _K.SPAN_OUTSIDE_UNIT)
    },
}

# The message of each code, a projection of it (coordinator decision 23).
MESSAGES: Mapping[IssueCode, str] = {
    _K.NOT_JSON: "the batch is not JSON: {detail}",
    _K.NOT_AN_OBJECT: "the batch is not a JSON object",
    _K.M11_FIELDS: "sympy and parse are set by M11 only, never in a batch: {detail}",
    _K.BINDING_FIELDS: "the binding of {symbol!r} has fields wrong for its kind: {detail}",
    _K.UNKNOWN_PREDICATE: "predicate {value!r} is not in the schema version",
    _K.UNKNOWN_CLASS: "class {value!r} is not an entity class of the schema version",
    _K.UNKNOWN_STATEMENT_KIND: "statement kind {value!r} is not in the schema version",
    _K.UNKNOWN_QUALIFIER: "qualifier {value!r} is not in the schema version",
    _K.UNKNOWN_MODALITY: "modality {value!r} is not in the schema version",
    _K.UNKNOWN_POLARITY: "polarity {value!r} is not a polarity",
    _K.UNKNOWN_SCOPE_EXTENT: "scope extent {value!r} is not a scope extent",
    _K.UNKNOWN_STATEMENT_ROLE: "statement role {value!r} is not a statement role",
    _K.UNKNOWN_BIND_KIND: "bind kind {value!r} is not a bind kind",
    _K.UNKNOWN_ENUM: "enum {value!r} is not in the schema version",
    _K.UNKNOWN_ENUM_VALUE: "{value!r} is not a member of the predicate's enum",
    _K.UNKNOWN_IDENTITY_SLOT: "{value!r} is not an identity slot of {cls}",
    _K.UNKNOWN_CONDITION_PREDICATE: "condition predicate {value!r} is not in the schema version",
    _K.SUBJECT_CLASS: "subject {ref!r} is a {cls}; {predicate} needs a {expected}",
    _K.OBJECT_CLASS: "object {ref!r} is a {cls}; {predicate} needs a {expected}",
    _K.OBJECT_KIND: "{predicate} takes a {expected} object, not {got}",
    _K.ENUM_NAME: "enum {value!r}; {predicate} takes {expected}",
    _K.QUALIFIER_NOT_ALLOWED: "{value!r} is not a qualifier of {predicate}",
    _K.QUALIFIER_CLASS: "qualifier {value} names {ref!r}, a {cls}; it takes a {expected}",
    _K.SCOPE_DISAGREES_WITH_CLASS: "{cls} is {expected} (ci:scope); the entity says {got}",
    _K.IDENTITY_KEYS_MISSING: "{cls} identity needs {missing}",
    _K.CONDITION_ARITY: "{value} takes {expected} arguments, not {got}",
    _K.CONDITION_ARG_CLASS: "{value} argument {ref!r} is a {cls}; it takes a {expected}",
    _K.DUPLICATE_LOCAL_REF: "local ref {ref!r} is already used by {other}",
    _K.UNRESOLVED_REF: "{what} {ref!r} names no item of the batch",
    _K.WRONG_REF_KIND: "{what} {ref!r} is a {got}; it takes {expected}",
    _K.BINDING_WRONG_REF_KIND: "the {bind} binding of {symbol!r} names {ref!r}, {got}; it needs "
    "{expected}",
    _K.BINDING_PARAM_MISSING: "claim {ref!r} has no {qualifier} entry {param!r}",
    _K.CONDITION_CLAIM_OUTSIDE_BATCH: "condition claim node {ref!r} names no claim of the batch",
    _K.CONDITION_CYCLE: "claim {ref!r} is on a condition reference cycle",
    _K.UNKNOWN_SENTENCE: "sentence id {value!r} is not in the frame",
    _K.UNCITED_REFERENCE: "the outside item's citing sentence {value!r} is not in the frame",
    _K.BAD_REFERENCE_TARGET: "link target {value!r} is neither a locator nor an author link target",
    _K.INV_01: "a stated claim has no primary evidence",
    _K.INV_02: "the object is {detail}",
    _K.INV_05: "{detail}",
    _K.INV_06: "a supposed claim is neither referenced by a condition nor scoped",
    _K.INV_10: "span ({start}, {end}) {detail}",
    _K.SPAN_OUTSIDE_UNIT: "span ({start}, {end}) lies outside the unit",
}

type Path = tuple[str | int, ...]


@dataclass(frozen=True)
class Issue:
    category: IssueCategory
    code: str  # an IssueCode, or a Pydantic error type for `malformed`
    path: Path
    message: str
    ref: str | None = None

    def line(self) -> str:
        return f"{self.category}\t{self.code}\t{'.'.join(map(str, self.path))}\t{self.message}"


@dataclass
class BatchReport:
    form: str
    issues: list[Issue] = field(default_factory=list)
    raw: Any = None

    @property
    def ok(self) -> bool:
        return not self.issues

    def categories(self) -> set[str]:
        return {i.category.value for i in self.issues}

    def codes(self) -> set[str]:
        return {i.code for i in self.issues}

    def pairs(self) -> set[tuple[str, str]]:
        return {(i.category.value, i.code) for i in self.issues}

    def lines(self) -> list[str]:
        return [i.line() for i in self.issues]

    def rejected_paths(self) -> list[tuple[str, int]]:
        """The items with an issue, as (section, index), in batch order."""
        found = {
            (i.path[0], i.path[1])
            for i in self.issues
            if len(i.path) >= 2 and i.path[0] in SECTIONS and isinstance(i.path[1], int)
        }
        return sorted(found, key=lambda p: (SECTIONS.index(str(p[0])), p[1]))

    def rejected(self) -> tuple[RejectedItem, ...]:
        """The rejected items in the `claim_proposal` payload's form: each item as written and
        the codes of its issues (D3 §6.2)."""
        out = []
        for section, index in self.rejected_paths():
            codes = sorted({i.code for i in self.issues if i.path[:2] == (section, index)})
            item = self.raw[section][index] if isinstance(self.raw, dict) else None
            out.append(RejectedItem(item=item, reason=", ".join(codes)))
        return tuple(out)


# --- The item adapters ------------------------------------------------------------------------


@dataclass(frozen=True)
class _Adapters:
    envelope: TypeAdapter[Any]
    items: Mapping[str, TypeAdapter[Any]]


_CACHE: dict[int, tuple[Any, dict[str, _Adapters]]] = {}


def _adapters(compiled: CompiledSchema, form: str) -> _Adapters:
    """The envelope and per-section item adapters of a compiled batch model (the compiled
    model's own item types, so items are judged exactly as the whole batch would be)."""
    batches = compiled.batches
    held = _CACHE.setdefault(id(batches), (batches, {}))[1]
    if form not in held:
        model = batches.models[form]
        items = {
            sec: TypeAdapter(typing.get_args(model.model_fields[sec].annotation)[0])
            for sec in SECTIONS
        }
        # the envelope's own fields, items taken as raw JSON (each item is judged on its own)
        base = B.AuthoredBatch if form == "model" else B.StoredBatch
        shell: Any = tuple
        fields: dict[str, Any] = {
            name: (info.annotation, info)
            for name, info in base.model_fields.items()
            if name not in SECTIONS
        }
        fields |= {sec: (shell[Any, ...], ()) for sec in SECTIONS}
        envelope = create_model(f"Envelope_{form}", __base__=V.CoreModel, **fields)
        held[form] = _Adapters(TypeAdapter(envelope), items)
    return held[form]


# --- The checks -------------------------------------------------------------------------------

_KINDS = {"entities": "entity", "claims": "claim", "unsupported": "unsupported"}
SUBJECT = frozenset({"entity", "statement", "outside"})
STATEMENT = frozenset({"statement"})
CLAIM_NODE = frozenset({"claim", "outside"})  # an ExternalReference stands for a statement outside
ENTITY = frozenset({"entity"})
CLAIM = frozenset({"claim"})


def _walk_values(node: Any, path: Path) -> Iterator[tuple[Path, dict[str, Any]]]:
    """Every formula or set value under `node`, with its path."""
    if isinstance(node, dict):
        if node.get("t") in ("formula", "set") and isinstance(node.get("symbols", {}), dict):
            yield path, node
        for k, v in node.items():
            if k != "symbols":
                yield from _walk_values(v, (*path, k))
    elif isinstance(node, list):
        for i, v in enumerate(node):
            yield from _walk_values(v, (*path, i))


def _nodes(tree: Any, path: Path) -> Iterator[tuple[Path, dict[str, Any]]]:
    """Every node of a condition tree, with its path."""
    if not isinstance(tree, dict) or "op" not in tree:
        return
    yield path, tree
    for i, arg in enumerate(tree.get("args", ()) if tree.get("op") in ("and", "or") else ()):
        yield from _nodes(arg, (*path, "args", i))
    for key in ("arg", "body"):
        if key in tree:
            yield from _nodes(tree[key], (*path, key))


def _claim_refs(node: Any) -> set[str]:
    out: set[str] = set()
    if isinstance(node, dict):
        if node.get("op") == "claim" and isinstance(node.get("ref"), str):
            out.add(node["ref"])
        for v in node.values():
            out |= _claim_refs(v)
    elif isinstance(node, list):
        for v in node:
            out |= _claim_refs(v)
    return out


def reference_target_ok(target: str) -> bool:
    """A D1 §3.4 locator, or an author link target (an in-page `#id` or a URL)."""
    if target.startswith("#") and len(target) > 1:
        return True
    if target.startswith(("http://", "https://")):
        return True
    try:
        locators.parse(target)
    except ValueError:
        return False
    return True


class _Check:
    def __init__(
        self,
        raw: Any,
        compiled: CompiledSchema,
        form: str,
        sentence_ids: Iterable[str] | None,
        canonical_text: str | None,
        unit_ranges: Iterable[tuple[int, int]] | None,
    ) -> None:
        if form not in FORMS:
            raise ValueError(f"form {form!r} is not one of {FORMS}")
        self.raw = raw
        self.compiled = compiled
        self.lookup = compiled.lookup
        self.names = compiled.names
        self.form = form
        self.sids = frozenset(sentence_ids) if sentence_ids is not None else None
        self.text = canonical_text
        self.units = list(unit_ranges) if unit_ranges is not None else None
        self.report = BatchReport(form, raw=raw)
        self.refs: dict[str, tuple[str, str, int]] = {}  # ref -> (kind, section, index)
        self.etype: dict[str, str] = {}  # ref -> local class
        self.escope: dict[str, str] = {}
        self.parsed: dict[str, list[tuple[int, dict[str, Any]]]] = {s: [] for s in SECTIONS}
        self.claims_raw: dict[str, dict[str, Any]] = {}
        self.parameter_classes = {
            e.name for e in self.lookup.entity_classes.values() if e.parameter_class
        }

    # -- reporting -----------------------------------------------------------------------------

    def add(self, code: IssueCode, path: Path, owner: str | None = None, **args: Any) -> None:
        message = MESSAGES[code].format(**({"ref": owner} | args))
        self.report.issues.append(Issue(CATEGORY[code], code.value, tuple(path), message, owner))

    def malformed(self, e: ErrorDetails, path: Path, ref: str | None) -> None:
        self.report.issues.append(
            Issue(IssueCategory.MALFORMED, e["type"], tuple(path), e["msg"], ref)
        )

    # -- names ---------------------------------------------------------------------------------

    def local(self, name: str) -> str:
        if self.form == "stored":
            if name.startswith(CORE) and name[len(CORE) :] in B.CORE_QUALIFIERS:
                return name[len(CORE) :]
            return self.names.to_local.get(name, name)
        return name

    def qualifiers(self, claim: Mapping[str, Any]) -> dict[str, Any]:
        """A claim's qualifiers by local name."""
        return {self.local(k): v for k, v in (claim.get("qualifiers") or {}).items()}

    def is_a(self, cls: str, target: str) -> bool:
        if target in self.lookup.ancestors.get(cls, ()):
            return True
        # an ExternalReference stands for a statement outside the batch (D1 §4.4)
        return cls == "ExternalReference" and target in self.lookup.ancestors.get("Statement", ())

    # -- structure -----------------------------------------------------------------------------

    def structure(self) -> bool:
        raw = self.raw
        if not isinstance(raw, dict):
            self.add(IssueCode.NOT_AN_OBJECT, ())
            return False
        adapters = _adapters(self.compiled, self.form)
        try:
            adapters.envelope.validate_json(json.dumps(raw), strict=True)
        except ValidationError as error:
            for e in error.errors():
                if not (e["loc"] and e["loc"][0] in SECTIONS and len(e["loc"]) > 1):
                    self.malformed(e, e["loc"], None)
        for sec in SECTIONS:
            items = raw.get(sec, [])
            if not isinstance(items, list):
                continue
            for i, item in enumerate(items):
                self.item(sec, i, item, adapters.items[sec])
        return True

    def item(self, sec: str, i: int, item: Any, adapter: TypeAdapter[Any]) -> None:
        ref = item.get("local_ref") if isinstance(item, dict) else None
        ref = ref if isinstance(ref, str) else None
        covered: set[Path] = set()  # error paths a semantic check reports instead
        if sec == "claims" and isinstance(item, dict):
            covered |= self.object_shape(i, item, ref)
        if sec == "entities" and isinstance(item, dict):
            covered |= self.entity_scope(i, item, ref)
        try:
            parsed = adapter.validate_json(json.dumps(item), strict=True)
            m11 = refuse_m11_fields(parsed)
            if m11:
                self.add(IssueCode.M11_FIELDS, (sec, i), ref, detail=", ".join(m11))
            elif isinstance(item, dict):
                self.parsed[sec].append((i, item))
        except ValidationError as error:
            for e in error.errors():
                self.classify(sec, i, item, e, ref, covered)
        if ref is None or sec == "alternatives":
            return
        kind = _KINDS.get(sec) or ("outside" if item.get("anchor") == "outside" else "statement")
        if ref in self.refs:
            other = self.refs[ref]
            self.add(
                IssueCode.DUPLICATE_LOCAL_REF,
                (sec, i, "local_ref"),
                ref,
                other=f"{other[1]}[{other[2]}]",
            )
            return
        self.refs[ref] = (kind, sec, i)
        if sec == "entities" and isinstance(item.get("type"), str):
            self.etype[ref] = self.local(item["type"])
            self.escope[ref] = str(item.get("scope"))
        elif sec == "statements":
            self.etype[ref] = "ExternalReference" if kind == "outside" else "Statement"
            self.escope[ref] = "local"
        elif sec == "claims":
            self.claims_raw[ref] = item

    def object_shape(self, i: int, item: dict[str, Any], ref: str | None) -> set[Path]:
        """INV-02 and the entity/value shape of the object against the predicate's kind; the
        Pydantic errors under the object are then reported by these instead."""
        loc: Path = ("claims", i, "object")
        obj = item.get("object")
        if obj is None:
            self.add(IssueCode.INV_02, loc, ref, detail="missing")
            return {("object",)}
        if not isinstance(obj, dict):
            return set()
        if "ref" in obj and "t" in obj:
            self.add(IssueCode.INV_02, loc, ref, detail="both an entity reference and a value")
            return {("object",)}
        predicate = self.lookup.predicates.get(self.local(str(item.get("predicate"))))
        if predicate is None:
            return set()
        is_ref = "ref" in obj
        if is_ref != (predicate.object_kind == "entity"):
            got = "an entity reference" if is_ref else f"a {obj.get('t')!s} value"
            self.add(
                IssueCode.OBJECT_KIND,
                loc,
                ref,
                predicate=predicate.prefixed,
                expected=predicate.object_kind,
                got=got,
            )
            return {("object",)}
        return set()

    def entity_scope(self, i: int, item: dict[str, Any], ref: str | None) -> set[Path]:
        """INV-05: a local entity has an extent (authored) or scope segment (stored), a global
        one neither; the model's item validator reports the same at the item, which this
        replaces."""
        loc: Path = ("entities", i)
        local = item.get("scope") == "local"
        if local and self.form == "model" and "extent" not in item:
            self.add(IssueCode.INV_05, (*loc, "extent"), ref, detail="a local entity has no extent")
        elif local and self.form == "stored" and "scope_segment" not in item:
            self.add(
                IssueCode.INV_05,
                (*loc, "scope_segment"),
                ref,
                detail="a local entity has no scope segment",
            )
        elif not local and ("extent" in item or "scope_segment" in item):
            self.add(
                IssueCode.INV_05,
                (*loc, "extent"),
                ref,
                detail="a global entity has an extent or scope segment",
            )
        else:
            return set()
        return {()}

    def classify(
        self, sec: str, i: int, item: Any, e: ErrorDetails, ref: str | None, covered: set[Path]
    ) -> None:
        loc: Path = tuple(e["loc"])
        if sec == "claims" and isinstance(item, dict) and loc and loc[0] == item.get("predicate"):
            loc = loc[1:]  # the discriminator's tag
        if sec == "statements" and loc and loc[0] in ("statement", "outside"):
            loc = loc[1:]
        if any(loc[: len(c)] == c for c in covered) and (loc or e["type"] == "value_error"):
            return
        path: Path = (sec, i, *loc)
        kind, value = e["type"], e.get("input")
        code: IssueCode | None = None
        args: dict[str, Any] = {"value": value}
        if sec == "claims" and loc == () and kind == "union_tag_invalid":
            code, path = IssueCode.UNKNOWN_PREDICATE, (*path, "predicate")
            args["value"] = item.get("predicate") if isinstance(item, dict) else None
        elif sec == "entities" and loc == ("type",) and kind == "literal_error":
            code = IssueCode.UNKNOWN_CLASS
        elif sec == "statements" and loc == ("kind",) and kind == "literal_error":
            code = IssueCode.UNKNOWN_STATEMENT_KIND
        elif loc == ("statement_role",) and kind == "enum":
            code = IssueCode.UNKNOWN_STATEMENT_ROLE
        elif "symbols" in loc and len(loc) > loc.index("symbols") + 1:
            at = loc.index("symbols")
            if loc[-1] == "bind" and kind == "enum":
                code = IssueCode.UNKNOWN_BIND_KIND
            else:
                code, path = IssueCode.BINDING_FIELDS, (sec, i, *loc[: at + 2])
                args = {"symbol": loc[at + 1], "detail": e["msg"]}
        elif len(loc) >= 2 and loc[0] == "qualifiers":
            code, args = self.qualifier_error(loc, kind, item, value)
        elif loc[:1] == ("object",) and loc[-1:] == ("v",) and kind == "literal_error":
            code = IssueCode.UNKNOWN_ENUM_VALUE
        elif loc[:1] == ("object",) and loc[-1:] == ("enum",) and kind == "literal_error":
            known = {self.local(e_.prefixed) for e_ in self.lookup.enums.values()}
            predicate = self.lookup.predicates.get(self.local(str(item.get("predicate"))))
            if self.local(str(value)) in known:
                code = IssueCode.ENUM_NAME
                args |= {
                    "predicate": item.get("predicate"),
                    "expected": predicate.range if predicate else "?",
                }
            else:
                code = IssueCode.UNKNOWN_ENUM
        if code is None:
            self.malformed(e, path, ref)
        else:
            self.add(code, path, ref, **args)

    def qualifier_error(
        self, loc: Path, kind: str, item: Any, value: Any
    ) -> tuple[IssueCode | None, dict[str, Any]]:
        name = self.local(str(loc[1]))
        args: dict[str, Any] = {"value": value}
        if len(loc) == 2 and kind == "extra_forbidden":
            predicate = self.lookup.predicates.get(self.local(str(item.get("predicate"))))
            args["value"] = name
            if name in self.lookup.qualifiers:
                args["predicate"] = predicate.prefixed if predicate else item.get("predicate")
                return IssueCode.QUALIFIER_NOT_ALLOWED, args
            return IssueCode.UNKNOWN_QUALIFIER, args
        if name == "modality" and len(loc) == 2 and kind == "literal_error":
            return IssueCode.UNKNOWN_MODALITY, args
        if name == "polarity" and len(loc) == 2 and kind == "enum":
            return IssueCode.UNKNOWN_POLARITY, args
        if name == "scope" and loc[-1] in ("scope", "extent", "core:scope") and kind == "enum":
            return IssueCode.UNKNOWN_SCOPE_EXTENT, args
        return None, args

    # -- references ----------------------------------------------------------------------------

    def need(
        self,
        ref: Any,
        kinds: frozenset[str],
        path: Path,
        owner: str | None,
        what: str,
        code: IssueCode = IssueCode.WRONG_REF_KIND,
        **extra: Any,
    ) -> TypeGuard[str]:
        """Whether `ref` names an item of one of `kinds`; reports why not."""
        if not isinstance(ref, str):
            return False
        held = self.refs.get(ref)
        if held is None:
            self.add(IssueCode.UNRESOLVED_REF, path, owner, what=what, ref=ref)
            return False
        if held[0] not in kinds:
            self.add(
                code,
                path,
                owner,
                what=what,
                ref=ref,
                got=f"a {held[0]}",
                expected=" or ".join(sorted(kinds)),
                **extra,
            )
            return False
        return True

    def sentence(self, sid: Any, path: Path, owner: str | None, code: IssueCode) -> None:
        if self.sids is not None and isinstance(sid, str) and sid not in self.sids:
            self.add(code, path, owner, value=sid)

    def span(self, node: Mapping[str, Any], path: Path, owner: str | None) -> None:
        start, end = node.get("start"), node.get("end")
        if not isinstance(start, int) or not isinstance(end, int):
            return
        text = self.text
        if text is not None:
            if not 0 <= start < end <= len(text):
                self.add(
                    IssueCode.INV_10,
                    path,
                    owner,
                    start=start,
                    end=end,
                    detail="lies outside the canonical text",
                )
                return
            quoted = node.get("text")
            if isinstance(quoted, str) and not node.get("coarse") and text[start:end] != quoted:
                self.add(
                    IssueCode.INV_10,
                    path,
                    owner,
                    start=start,
                    end=end,
                    detail="differs from its text",
                )
        if self.units is not None and not any(s <= start and end <= e for s, e in self.units):
            self.add(IssueCode.SPAN_OUTSIDE_UNIT, path, owner, start=start, end=end)

    def anchored(self, node: Mapping[str, Any], path: Path, owner: str | None) -> None:
        """Text anchored by sentence (authored) or by span (stored)."""
        if self.form == "model":
            self.sentence(node.get("sentence"), path, owner, IssueCode.UNKNOWN_SENTENCE)
        else:
            self.span(node, path, owner)

    def bindings(self, value: Mapping[str, Any], path: Path, owner: str | None) -> None:
        for symbol, b in (value.get("symbols") or {}).items():
            if not isinstance(b, dict):
                continue
            at: Path = (*path, "symbols", symbol)
            bind = b.get("bind")
            args = {"bind": bind, "symbol": symbol}
            if bind in ("variable", "family_param"):
                r = b.get("entity")
                if not self.need(
                    r,
                    ENTITY,
                    at,
                    owner,
                    "binding entity",
                    IssueCode.BINDING_WRONG_REF_KIND,
                    bind=bind,
                    symbol=symbol,
                ):
                    continue
                cls = self.etype.get(r, "")
                if bind == "variable" and self.escope.get(r) != "local":
                    self.add(
                        IssueCode.BINDING_WRONG_REF_KIND,
                        at,
                        owner,
                        ref=r,
                        **args,
                        got=f"a {self.escope.get(r)} {cls}",
                        expected="a local entity",
                    )
                elif bind == "family_param" and not any(
                    self.is_a(cls, p) for p in self.parameter_classes
                ):
                    self.add(
                        IssueCode.BINDING_WRONG_REF_KIND,
                        at,
                        owner,
                        ref=r,
                        **args,
                        got=f"a {cls}",
                        expected="a parameter class entity",
                    )
            elif bind in ("param_of", "param_expr_of"):
                r = b.get("claim")
                if not self.need(
                    r,
                    CLAIM_NODE,
                    at,
                    owner,
                    "binding claim",
                    IssueCode.BINDING_WRONG_REF_KIND,
                    bind=bind,
                    symbol=symbol,
                ):
                    continue
                target = self.claims_raw.get(r)
                if target is None:
                    continue  # an ExternalReference: its parameters are outside the batch
                predicate = self.lookup.predicates.get(self.local(str(target.get("predicate"))))
                qualifier = predicate.param_map if predicate else None
                entries = self.qualifiers(target).get(qualifier or "") if qualifier else None
                if not isinstance(entries, dict) or b.get("param") not in entries:
                    self.add(
                        IssueCode.BINDING_PARAM_MISSING,
                        at,
                        owner,
                        ref=r,
                        qualifier=qualifier or "ci:param_map",
                        param=b.get("param"),
                    )

    def tree(self, tree: Any, path: Path, owner: str | None) -> None:
        for at, node in _nodes(tree, path):
            op = node.get("op")
            if op == "claim":
                r = node.get("ref")
                if str(r) not in self.refs:
                    self.add(IssueCode.CONDITION_CLAIM_OUTSIDE_BATCH, at, owner, ref=r)
                else:
                    self.need(r, CLAIM_NODE, at, owner, "condition claim node")
            elif op == "pred":
                self.pred(node, at, owner)
            elif op in ("phrase", "unsupported"):
                self.anchored(node, at, owner)

    def pred(self, node: Mapping[str, Any], at: Path, owner: str | None) -> None:
        name, args = node.get("name"), list(node.get("args") or ())
        cp = self.lookup.condition_predicates.get(str(name))
        if cp is None:
            self.add(IssueCode.UNKNOWN_CONDITION_PREDICATE, (*at, "name"), owner, value=name)
            return
        arity = cp.arity or ""
        if (arity.endswith("+") and arity[:-1].isdigit() and len(args) < int(arity[:-1])) or (
            arity.isdigit() and len(args) != int(arity)
        ):
            self.add(
                IssueCode.CONDITION_ARITY, at, owner, value=name, expected=arity, got=len(args)
            )
        for k, arg in enumerate(args):
            if isinstance(arg, dict) and "ref" in arg:
                r = arg["ref"]
                if self.need(r, ENTITY, (*at, "args", k), owner, "condition argument") and cp.args:
                    cls = self.etype.get(r, "")
                    if not self.is_a(cls, cp.args):
                        self.add(
                            IssueCode.CONDITION_ARG_CLASS,
                            (*at, "args", k),
                            owner,
                            value=name,
                            ref=r,
                            cls=cls,
                            expected=cp.args,
                        )

    # -- items ---------------------------------------------------------------------------------

    def entities(self) -> None:
        for i, e in self.parsed["entities"]:
            loc: Path = ("entities", i)
            ref, cls = e["local_ref"], self.local(e["type"])
            ec = self.lookup.entity_classes.get(cls)
            if ec is None:
                continue
            if ec.scope and ec.scope != e["scope"]:
                self.add(
                    IssueCode.SCOPE_DISAGREES_WITH_CLASS,
                    (*loc, "scope"),
                    ref,
                    cls=cls,
                    expected=ec.scope,
                    got=e["scope"],
                )
            keys = {self.names.to_local[k] for k in ec.identity_keys}
            entity_slots = {self.names.to_local[k] for k in ec.entity_identity}
            identity = {self.local(k): v for k, v in (e.get("identity") or {}).items()}
            for slot, value in identity.items():
                at: Path = (*loc, "identity", slot)
                if slot not in keys:
                    self.add(IssueCode.UNKNOWN_IDENTITY_SLOT, at, ref, value=slot, cls=cls)
                elif slot in entity_slots:
                    self.need(value, ENTITY | STATEMENT, at, ref, f"identity {slot}")
            missing = sorted(keys - set(identity))
            if missing:
                self.add(
                    IssueCode.IDENTITY_KEYS_MISSING,
                    (*loc, "identity"),
                    ref,
                    cls=cls,
                    missing=missing,
                )

    def statements(self) -> None:
        for i, s in self.parsed["statements"]:
            loc: Path = ("statements", i)
            ref = s["local_ref"]
            if s.get("anchor") == "outside":
                d = s.get("descriptor") or {}
                at: Path = (*loc, "descriptor")
                if self.form == "model":
                    self.sentence(
                        d.get("sentence"), (*at, "sentence"), ref, IssueCode.UNCITED_REFERENCE
                    )
                else:
                    self.span(d, at, ref)
                target = d.get("target")
                if isinstance(target, str) and not reference_target_ok(target):
                    self.add(IssueCode.BAD_REFERENCE_TARGET, (*at, "target"), ref, value=target)
            elif self.form == "model" and isinstance(s.get("anchor"), list):
                for k, sid in enumerate(s["anchor"]):
                    self.sentence(sid, (*loc, "anchor", k), ref, IssueCode.UNKNOWN_SENTENCE)

    def claims(self) -> None:
        referenced: set[str] = set()
        edges: dict[str, set[str]] = {}
        for i, c in self.parsed["claims"]:
            loc: Path = ("claims", i)
            ref = c["local_ref"]
            predicate = self.lookup.predicates[self.local(c["predicate"])]
            subject = c.get("subject")
            if self.need(subject, SUBJECT, (*loc, "subject"), ref, "subject"):
                cls = self.etype.get(subject, "")
                if not self.is_a(cls, predicate.domain):
                    self.add(
                        IssueCode.SUBJECT_CLASS,
                        (*loc, "subject"),
                        ref,
                        ref=subject,
                        cls=cls,
                        predicate=predicate.prefixed,
                        expected=predicate.domain,
                    )
            obj = c.get("object") or {}
            if "ref" in obj and self.need(obj["ref"], SUBJECT, (*loc, "object"), ref, "object"):
                cls = self.etype.get(obj["ref"], "")
                if not self.is_a(cls, predicate.range):
                    self.add(
                        IssueCode.OBJECT_CLASS,
                        (*loc, "object"),
                        ref,
                        ref=obj["ref"],
                        cls=cls,
                        predicate=predicate.prefixed,
                        expected=predicate.range,
                    )
            if "statement" in c:
                self.need(c["statement"], STATEMENT, (*loc, "statement"), ref, "statement")
            raw_quals = c.get("qualifiers") or {}
            for raw_name, value in raw_quals.items():
                name = self.local(raw_name)
                q = self.lookup.qualifiers.get(name)
                at: Path = (*loc, "qualifiers", raw_name)
                if q is None:
                    continue
                if q.object_kind == "entity" and isinstance(value, dict):
                    r = value.get("ref")
                    if self.need(r, SUBJECT, at, ref, f"qualifier {name}"):
                        cls = self.etype.get(r, "")
                        if not self.is_a(cls, q.range):
                            self.add(
                                IssueCode.QUALIFIER_CLASS,
                                at,
                                ref,
                                value=name,
                                ref=r,
                                cls=cls,
                                expected=q.range,
                            )
                elif q.object_kind == "condition":
                    self.tree(value, at, ref)
                    found = _claim_refs(value)
                    referenced |= found
                    edges.setdefault(ref, set()).update(found)
                elif q.object_kind == "phrase" and isinstance(value, dict):
                    self.anchored(value, at, ref)
            for at, value in _walk_values({"object": obj, "qualifiers": raw_quals}, loc):
                self.bindings(value, at, ref)
            if obj.get("t") == "phrase":
                self.anchored(obj, (*loc, "object"), ref)
            evidence = c.get("evidence") or []
            if c.get("establishment", "stated") == "stated" and not any(
                isinstance(ev, dict) and ev.get("role") == "primary" for ev in evidence
            ):
                self.add(IssueCode.INV_01, (*loc, "evidence"), ref)
            for k, ev in enumerate(evidence):
                self.anchored(ev, (*loc, "evidence", k), ref)
        # INV-06: references harvested from every claim as written, parsed or not
        for c in self.claims_raw.values():
            referenced |= _claim_refs(c.get("qualifiers"))
        for i, c in self.parsed["claims"]:
            quals = self.qualifiers(c)
            if (
                quals.get("modality") == "supposed"
                and c["local_ref"] not in referenced
                and "scope" not in quals
            ):
                self.add(IssueCode.INV_06, ("claims", i), c["local_ref"])
        self.cycles(edges)

    def cycles(self, edges: Mapping[str, set[str]]) -> None:
        """Condition reference cycles (D5 §5.2), each claim on one reported once."""
        state: dict[str, int] = {}
        on_cycle: set[str] = set()

        def visit(u: str, path: list[str]) -> None:
            state[u] = 1
            path.append(u)
            for v in sorted(edges.get(u, ())):
                if state.get(v) == 1:
                    on_cycle.update(path[path.index(v) :])
                elif v not in state:
                    visit(v, path)
            path.pop()
            state[u] = 2

        for u in sorted(edges):
            if u not in state:
                visit(u, [])
        for u in sorted(on_cycle):
            self.add(IssueCode.CONDITION_CYCLE, ("claims", self.refs[u][2]), u, ref=u)

    def rest(self) -> None:
        for i, a in self.parsed["alternatives"]:
            for k, r in enumerate(a.get("refs") or ()):
                self.need(r, CLAIM, ("alternatives", i, "refs", k), None, "alternative member")
        for i, u in self.parsed["unsupported"]:
            self.anchored(u, ("unsupported", i), u.get("local_ref"))

    def run(self) -> BatchReport:
        if self.structure():
            self.entities()
            self.statements()
            self.claims()
            self.rest()
        return self.report


def check_batch(
    batch_json: str | Mapping[str, Any],
    compiled: CompiledSchema,
    form: str,
    *,
    sentence_ids: Iterable[str] | None = None,
    canonical_text: str | None = None,
    unit_ranges: Sequence[tuple[int, int]] | None = None,
) -> BatchReport:
    """The batch's issues in one report (module doc). `sentence_ids` (authored form) enables the
    frame checks; `canonical_text` and `unit_ranges` (stored form) enable INV-10 and the
    inside-the-unit check."""
    if isinstance(batch_json, str):
        try:
            raw: Any = json.loads(batch_json)
        except json.JSONDecodeError as error:
            report = BatchReport(form)
            report.issues.append(
                Issue(
                    IssueCategory.MALFORMED,
                    IssueCode.NOT_JSON.value,
                    (),
                    MESSAGES[IssueCode.NOT_JSON].format(detail=error.msg),
                )
            )
            return report
    else:
        raw = json.loads(json.dumps(batch_json))
    return _Check(raw, compiled, form, sentence_ids, canonical_text, unit_ranges).run()
