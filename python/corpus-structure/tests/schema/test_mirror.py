"""The interim mirror guard (TM §12; model and projections §3.2): until Stage B generates the shapes
(P0-M-5), every shape fact Stage A does not generate is compared between the hand-written Pydantic
shapes and `model/core.yaml`, through `SchemaView`.

Per batch form (`model` is the authored form): each class's fields (an attribute counts in a form
by its `ci:form`; a `consolidated` one in both), their required-ness (`required`, or
`ci:required_in` for that form) and multivalued-ness, the value and condition tags (`t`, `op`), the
static enum each enum-ranged field takes, and the core qualifiers with their stored aliases and
the form-dependent `scope` range (`ci:stored_range`). The closed sets themselves (bind kinds,
evidence roles, …) and the binding fields per kind are generated, so they are not compared here.
A seeded difference on either side fails.

The source-profile half compares ingest's profile model (`ingest/profile.py`, P0-I-1a) and its
build diagnostics (`core/parse_detail.py`, the `parse_detail` payload) with their classes in
`model/system.yaml` the same way: each class's fields, their required-ness
(`required`, or an `identifier`, which the YAML writes as the key of an inlined mapping) and
multivalued-ness, the generated enum each enum-ranged field takes, and the paired profile class each
class-ranged field takes. The profile model's field validation (selectors, prefixed names) is its
own and is tested with it.

The payload half (F2e) compares the observation payload and operations JSON models
(`core/payloads.py`) with their `system.yaml` classes: each class's fields, required-ness and
multivalued-ness (an opaque `Json` slot is one document, whatever its Python shape), whether a
multivalued class-ranged field is keyed (a dict by the range's `identifier`, against a list), the
static enum each enum-ranged field takes, and a scalar-ranged field's Python types. So a payload
whose shape drifts from its model class fails here.
"""

from __future__ import annotations

import types
import typing
from pathlib import Path
from typing import Any

import pytest
import yaml
from linkml_runtime.utils.schemaview import SchemaView
from pydantic import BaseModel, create_model

from corpus_structure.core import batch, candidates, payloads, values, vocab
from corpus_structure.core import parse_detail as parse_details
from corpus_structure.ingest import profile as profiles
from corpus_structure.schema.model import CORE, SYSTEM, ci_annotations

V, B, C = values, batch, candidates
BOTH = ("model", "stored")

# model class -> (authored shape, stored shape); None where a form has no such class
PAIRS: dict[str, tuple[type[BaseModel] | None, type[BaseModel] | None]] = {
    "TextValue": (V.TextValue, V.TextValue),
    "NumberValue": (V.NumberValue, V.NumberValue),
    "BoolValue": (V.BoolValue, V.BoolValue),
    "EnumValue": (V.AuthoredEnumValue, V.StoredEnumValue),
    "Formula": (V.Formula, V.Formula),
    "SetExpr": (V.SetValue, V.SetValue),
    "DateValue": (V.DateValue, V.DateValue),
    "IntervalValue": (V.IntervalValue, V.IntervalValue),
    "PhraseValue": (V.AuthoredPhrase, V.StoredPhrase),
    "EntityRef": (V.EntityRef, V.EntityRef),
    "SymbolBinding": (V.SymbolBinding, V.SymbolBinding),
    "AndNode": (V.AuthoredAnd, V.StoredAnd),
    "OrNode": (V.AuthoredOr, V.StoredOr),
    "NotNode": (V.AuthoredNot, V.StoredNot),
    "ForallNode": (V.AuthoredForall, V.StoredForall),
    "ClaimNode": (V.ClaimNode, V.ClaimNode),
    "MemberNode": (V.MemberNode, V.MemberNode),
    "CmpNode": (V.CmpNode, V.CmpNode),
    "PredNode": (V.PredNode, V.PredNode),
    "PhraseNode": (V.AuthoredPhraseNode, V.StoredPhraseNode),
    "UnsupportedNode": (V.AuthoredUnsupportedNode, V.StoredUnsupportedNode),
    "StoredScope": (None, B.StoredScope),
    "Evidence": (B.AuthoredEvidence, B.StoredEvidence),
    "EntityItem": (B.AuthoredEntity, B.StoredEntity),
    "StatementItem": (B.AuthoredStatement, B.StoredStatement),
    "OutsideItem": (B.AuthoredOutside, B.StoredOutside),
    "ReferenceDescriptor": (B.AuthoredDescriptor, B.StoredDescriptor),
    "ClaimItem": (B.AuthoredClaim, B.StoredClaim),
    "AlternativeItem": (B.AlternativeItem, B.AlternativeItem),
    "UnsupportedItem": (B.AuthoredUnsupported, B.StoredUnsupported),
    "Batch": (B.AuthoredBatch, B.StoredBatch),
    # the keyed candidate set: stored form only (F2e, TM §3)
    **{name: (None, getattr(C, name)) for name in (
        "CandidateEntity", "CandidateStatement", "CandidateReference", "CandidateClaim",
        "CandidateAlternative", "CandidateUnsupported", "KeyedCandidateSet")},
}

STATIC_ENUMS = {
    cls.__name__: cls for cls, lc in vocab.LIFECYCLE.items() if lc is vocab.Lifecycle.STATIC
}


def _members(annotation: Any) -> list[Any]:
    """The types a field annotation names, through unions, `Annotated` and containers."""
    if typing.get_origin(annotation) is typing.Annotated:
        return _members(typing.get_args(annotation)[0])
    if isinstance(annotation, typing.TypeAliasType):
        return _members(annotation.__value__)
    origin = typing.get_origin(annotation)
    if origin in (typing.Union, types.UnionType, tuple, dict, typing.Literal):
        out = [annotation] if origin is typing.Literal else []
        for arg in typing.get_args(annotation):
            if arg is not Ellipsis and origin is not typing.Literal:
                out += _members(arg)
        return out
    return [annotation]


def _non_missing(annotation: Any) -> list[Any]:
    if typing.get_origin(annotation) in (typing.Union, types.UnionType):
        return [a for a in typing.get_args(annotation) if repr(a) != "MISSING"]
    return [annotation]


def hand_facts(cls: type[BaseModel]) -> dict[str, tuple[bool, bool | None]]:
    out: dict[str, tuple[bool, bool | None]] = {}
    for name, info in cls.model_fields.items():
        kinds = _non_missing(info.annotation)
        multivalued = None
        if len(kinds) == 1:
            base = kinds[0]
            if typing.get_origin(base) is typing.Annotated:
                base = typing.get_args(base)[0]
            multivalued = typing.get_origin(base) in (tuple, dict)
        out[name] = (info.is_required(), multivalued)
    return out


def model_facts(view: Any, cls: str, form: str) -> dict[str, tuple[bool, bool, Any]]:
    out: dict[str, tuple[bool, bool, Any]] = {}
    for slot in view.class_induced_slots(cls):
        ann = ci_annotations(slot)
        present_in = ann.get("ci:form")
        if present_in not in (None, form, "consolidated"):
            continue
        required = bool(slot.required) or ann.get("ci:required_in") == form
        out[str(slot.name)] = (required, bool(slot.multivalued), slot)
    return out


def differences(view: Any, pairs: dict = PAIRS) -> list[str]:
    found: list[str] = []
    for cls, shapes in pairs.items():
        for form, shape in zip(BOTH, shapes, strict=True):
            if shape is None:
                continue
            where = f"{cls}/{form} ({shape.__name__})"
            mine, theirs = model_facts(view, cls, form), hand_facts(shape)
            for name in sorted(set(mine) ^ set(theirs)):
                side = "the model" if name in mine else "the Pydantic shape"
                found.append(f"{where}: only {side} has {name!r}")
            for name in sorted(set(mine) & set(theirs)):
                required, multivalued, slot = mine[name]
                hand_required, hand_multivalued = theirs[name]
                if required != hand_required:
                    found.append(f"{where}.{name}: required {required} vs {hand_required}")
                if hand_multivalued is not None and multivalued != hand_multivalued:
                    found.append(f"{where}.{name}: multivalued {multivalued} vs {hand_multivalued}")
                annotation = shape.model_fields[name].annotation
                if name in ("t", "op") and slot.equals_string:
                    tags = [typing.get_args(a) for a in _members(annotation)
                            if typing.get_origin(a) is typing.Literal]  # fmt: skip
                    if tags != [(slot.equals_string,)]:
                        found.append(f"{where}.{name}: tag {slot.equals_string!r} vs {tags}")
                rng = str(slot.range)
                if rng in STATIC_ENUMS and STATIC_ENUMS[rng] not in _members(annotation):
                    found.append(f"{where}.{name}: the shape does not take {rng}")
    found += _qualifier_differences(view)
    return found


def _qualifier_differences(view: Any) -> list[str]:
    found: list[str] = []
    core = [str(n) for n, s in view.schema.slots.items()
            if ci_annotations(s).get("ci:role") == "qualifier"]  # fmt: skip
    for form, shape in (("model", batch.AuthoredQualifiers), ("stored", batch.StoredQualifiers)):
        fields = shape.model_fields
        if set(fields) != set(core):
            found.append(f"qualifiers/{form}: {sorted(fields)} vs the model's {sorted(core)}")
        for name in set(fields) & set(core):
            slot = view.get_slot(name)
            alias = fields[name].alias
            if form == "stored" and alias != f"core:{name}":
                found.append(f"qualifiers/stored.{name}: alias {alias!r}")
            rng = ci_annotations(slot).get("ci:stored_range") if form == "stored" else None
            rng = str(rng or slot.range)
            named = {getattr(m, "__name__", None) for m in _members(fields[name].annotation)}
            hand_range = {"Condition": {"AuthoredAnd", "StoredAnd"},
                          # a schema-version-scoped set admits pack members: a name, not the enum
                          "ClaimModality": {"str"},
                          "PhraseValue": {"AuthoredPhrase", "StoredPhrase"},
                          "Entity": {"EntityRef"}}.get(rng, {rng})  # fmt: skip
            if not named & hand_range:
                found.append(f"qualifiers/{form}.{name}: range {rng} vs {sorted(map(str, named))}")
    return found


@pytest.fixture(scope="module")
def view() -> SchemaView:
    return SchemaView(str(CORE))


def test_the_hand_shapes_mirror_the_model(view: SchemaView) -> None:
    assert differences(view) == []


def _attr(data: dict, cls: str, name: str) -> dict:
    return data["classes"][cls]["attributes"][name]


def edited_view(tmp_path: Path, edit) -> SchemaView:
    data = yaml.safe_load(CORE.read_text(encoding="utf-8"))
    edit(data)
    path = tmp_path / "core.yaml"
    path.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")
    return SchemaView(str(path))


@pytest.mark.parametrize(
    ("edit", "expected"),
    [
        (lambda d: d["classes"]["NumberValue"]["attributes"].pop("basis"),
         "NumberValue/model (NumberValue): only the Pydantic shape has 'basis'"),
        (lambda d: d["classes"]["TextValue"]["attributes"].update({"lang": {"description": "x"}}),
         "TextValue/stored (TextValue): only the model has 'lang'"),
        (lambda d: _attr(d, "PhraseValue", "start")["annotations"].pop("ci:required_in"),
         "PhraseValue/stored (StoredPhrase).start: required False vs True"),
        (lambda d: _attr(d, "Evidence", "quote")["annotations"].update({"ci:form": "stored"}),
         "Evidence/model (AuthoredEvidence): only the Pydantic shape has 'quote'"),
        (lambda d: d["classes"]["CmpNode"]["slot_usage"]["op"].update({"equals_string": "compare"}),
         "CmpNode/model (CmpNode).op: tag 'compare'"),
        (lambda d: d["slots"]["scope"]["annotations"].pop("ci:stored_range"),
         "qualifiers/stored.scope: range ScopeExtent"),
        (lambda d: d["slots"].update({"weight": {"description": "x",
                                                 "annotations": {"ci:role": "qualifier"}}}),
         "qualifiers/model:"),
    ],
)  # fmt: skip
def test_a_seeded_model_side_difference_fails(tmp_path: Path, edit, expected: str) -> None:
    found = differences(edited_view(tmp_path, edit))
    assert any(expected in f for f in found), found


def test_a_seeded_shape_side_difference_fails(view: SchemaView) -> None:
    with_lang = create_model("TextValue", __base__=values.TextValue, lang=(str, ...))
    found = differences(view, {**PAIRS, "TextValue": (with_lang, values.TextValue)})
    assert found == ["TextValue/model (TextValue): only the Pydantic shape has 'lang'"]
    loose = create_model("SymbolBinding", __base__=values.SymbolBinding, bind=(str, ...))
    found = differences(view, {**PAIRS, "SymbolBinding": (loose, loose)})
    assert "SymbolBinding/model (SymbolBinding).bind: the shape does not take BindKind" in found


# --- The payload half --------------------------------------------------------------------------

PL = payloads
# system class -> the payload or operations JSON model of `core/payloads.py`
PAYLOAD_PAIRS: dict[str, type[BaseModel]] = {
    name: getattr(PL, name) for name in (
        "AttributePayload", "AuthorMarkupPayload", "ClaimProposalPayload", "ClassificationPayload",
        "GoldenBatchPayload",
        "InterventionTarget", "JudgmentPayload", "JudgmentTarget", "LabelScore", "LabelledSpan",
        "LinkPayload", "MentionAt", "MentionPayload", "MentionRef", "NewEntity", "PolicyAction",
        "RecordField", "RecordPayload", "RejectedItem", "RelationPayload", "ScopePayload",
        "SynthesizedClaim", "ValuePayload", "VerificationDetail", "VerificationPayload",
    )
} | {"TaskCost": PL.Cost}  # fmt: skip
SCALARS: dict[str, set[type]] = {"string": {str}, "integer": {int}, "boolean": {bool},
                                 "Real": {float}}  # fmt: skip


def _single(annotation: Any) -> Any:
    kinds = _non_missing(annotation)
    base = kinds[0] if len(kinds) == 1 else None
    return typing.get_args(base)[0] if typing.get_origin(base) is typing.Annotated else base


def payload_differences(view: Any, pairs: dict[str, type[BaseModel]] = PAYLOAD_PAIRS) -> list[str]:
    found: list[str] = []
    for cls, shape in pairs.items():
        where = f"{cls} ({shape.__name__})"
        slots = {str(slot.name): slot for slot in view.class_induced_slots(cls)}
        theirs = hand_facts(shape)
        for name in sorted(set(slots) ^ set(theirs)):
            side = "the model" if name in slots else "the Pydantic shape"
            found.append(f"{where}: only {side} has {name!r}")
        for name in sorted(set(slots) & set(theirs)):
            slot, (hand_required, hand_multivalued) = slots[name], theirs[name]
            rng = str(slot.range)
            if bool(slot.required) != hand_required:
                found.append(f"{where}.{name}: required {bool(slot.required)} vs {hand_required}")
            if (rng != "Json" and hand_multivalued is not None
                    and bool(slot.multivalued) != hand_multivalued):  # fmt: skip
                found.append(f"{where}.{name}: multivalued {bool(slot.multivalued)} vs "
                             f"{hand_multivalued}")  # fmt: skip
            annotation = shape.model_fields[name].annotation
            if slot.multivalued and view.get_class(rng) is not None:
                keyed = not slot.inlined_as_list and any(
                    s.identifier for s in view.class_induced_slots(rng))
                hand_keyed = typing.get_origin(_single(annotation)) is dict
                if keyed != hand_keyed:
                    found.append(f"{where}.{name}: keyed {keyed} vs {hand_keyed}")
            if rng in STATIC_ENUMS and STATIC_ENUMS[rng] not in _members(annotation):
                found.append(f"{where}.{name}: the shape does not take {rng}")
            if rng in SCALARS and not slot.multivalued:
                hand = {m for m in _members(annotation) if isinstance(m, type)}
                if hand != SCALARS[rng]:
                    found.append(f"{where}.{name}: range {rng} vs "
                                 f"{sorted(t.__name__ for t in hand)}")  # fmt: skip
    return found


@pytest.fixture(scope="module")
def payload_view() -> SchemaView:
    return SchemaView(str(SYSTEM))


def test_the_payload_models_mirror_the_system_classes(payload_view: SchemaView) -> None:
    assert payload_differences(payload_view) == []


@pytest.mark.parametrize(
    ("shape", "field", "annotation", "expected"),
    [
        # the drift M3/M4 found, seeded back: a ref that takes an int, attributes as a list
        ("InterventionTarget", "ref", (str | int, ...),
         "InterventionTarget (InterventionTarget).ref: range string vs ['int', 'str']"),
        ("MentionPayload", "attributes", (tuple[PL.LabelScore, ...], ()),
         "MentionPayload (MentionPayload).attributes: keyed True vs False"),
        ("Cost", "wall_ms", (int, 0), "TaskCost (Cost).wall_ms: required True vs False"),
        ("VerificationDetail", "severity", (str, ...),
         "VerificationDetail (VerificationDetail).severity: the shape does not take RuleSeverity"),
    ],
)  # fmt: skip
def test_a_seeded_payload_side_difference_fails(
    payload_view: SchemaView, shape: str, field: str, annotation: Any, expected: str
) -> None:
    base: type[BaseModel] = getattr(PL, shape)
    fields: dict[str, Any] = {field: annotation}
    drifted = create_model(shape, __base__=base, **fields)
    cls = "TaskCost" if shape == "Cost" else shape
    found = payload_differences(payload_view, {cls: drifted})
    assert expected in found, found


def test_a_seeded_model_side_payload_difference_fails(tmp_path: Path) -> None:
    def edit(classes: dict) -> None:
        classes["MentionPayload"]["attributes"]["attributes"]["range"] = "LabelScore"
        classes["JudgmentPayload"]["attributes"]["rationale"].pop("required")

    view = edited_system(tmp_path, edit)
    assert payload_differences(view) == [
        "JudgmentPayload (JudgmentPayload).rationale: required False vs True",
        "MentionPayload (MentionPayload).attributes: keyed False vs True",
    ]


# --- The source-profile half -------------------------------------------------------------------

P, D = profiles, parse_details
# system class -> ingest's model class: the source profile, and the build diagnostics payload
PROFILE_PAIRS: dict[str, type[BaseModel]] = {
    "SourceProfile": P.SourceProfile,
    "CorpusIndex": P.CorpusIndex,
    "ExcludeRule": P.ExcludeRule,
    "BlockHint": P.BlockHint,
    "SectionHint": P.SectionHint,
    "DetailsKinds": P.DetailsKinds,
    "SummaryKind": P.SummaryKind,
    "SynthesisRule": P.SynthesisRule,
    "MathSpec": P.MathSpec,
    "ReferenceSpec": P.ReferenceSpec,
    "RenderSpec": P.RenderSpec,
    "ListMarkerRule": P.ListMarkerRule,
    "ParseDetail": D.ParseDetail,
    "ParserError": D.ParserError,
    "RoleConflict": D.RoleConflict,
    "ExcludedElement": D.ExcludedElement,
    "MathAnomaly": D.MathAnomaly,
    "OrphanRun": D.OrphanRun,
    "UnicodeChange": D.UnicodeChange,
}
ENUMS = {name: obj for name, obj in vars(vocab).items()
         if isinstance(obj, type) and issubclass(obj, vocab.StrEnum)}  # fmt: skip


def profile_differences(view: Any, pairs: dict[str, type[BaseModel]] = PROFILE_PAIRS) -> list[str]:
    found: list[str] = []
    for cls, shape in pairs.items():
        where = f"{cls} ({shape.__name__})"
        slots = {str(slot.name): slot for slot in view.class_induced_slots(cls)}
        theirs = hand_facts(shape)
        for name in sorted(set(slots) ^ set(theirs)):
            side = "the model" if name in slots else "the Pydantic shape"
            found.append(f"{where}: only {side} has {name!r}")
        for name in sorted(set(slots) & set(theirs)):
            slot = slots[name]
            required = bool(slot.required or slot.identifier)
            hand_required, hand_multivalued = theirs[name]
            if required != hand_required:
                found.append(f"{where}.{name}: required {required} vs {hand_required}")
            if hand_multivalued is not None and bool(slot.multivalued) != hand_multivalued:
                found.append(f"{where}.{name}: multivalued {bool(slot.multivalued)} vs "
                             f"{hand_multivalued}")  # fmt: skip
            rng = str(slot.range)
            expected = ENUMS.get(rng) or pairs.get(rng)
            annotation = shape.model_fields[name].annotation
            if expected is not None and expected not in _members(annotation):
                found.append(f"{where}.{name}: the shape does not take {rng}")
    return found


@pytest.fixture(scope="module")
def system_view() -> SchemaView:
    return SchemaView(str(SYSTEM))


def test_the_profile_model_mirrors_the_system_classes(system_view: SchemaView) -> None:
    assert profile_differences(system_view) == []


def edited_system(tmp_path: Path, edit) -> SchemaView:
    data = yaml.safe_load(SYSTEM.read_text(encoding="utf-8"))
    edit(data["classes"])
    (tmp_path / "core.yaml").write_text(CORE.read_text(encoding="utf-8"), encoding="utf-8")
    path = tmp_path / "system.yaml"
    path.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")
    return SchemaView(str(path))


@pytest.mark.parametrize(
    ("edit", "expected"),
    [
        (lambda c: c["SourceProfile"]["attributes"].pop("img_alt"),
         "SourceProfile (SourceProfile): only the Pydantic shape has 'img_alt'"),
        (lambda c: c["RenderSpec"]["attributes"].update({"em": {"description": "x"}}),
         "RenderSpec (RenderSpec): only the model has 'em'"),
        (lambda c: c["CorpusIndex"]["attributes"]["page"].pop("required"),
         "CorpusIndex (CorpusIndex).page: required False vs True"),
        (lambda c: c["SourceProfile"]["attributes"]["sections"].pop("multivalued"),
         "SourceProfile (SourceProfile).sections: multivalued False vs True"),
        (lambda c: c["BlockHint"]["attributes"]["statement_kind"].update({"range": "SegmentKind"}),
         "BlockHint (BlockHint).statement_kind: the shape does not take SegmentKind"),
        (lambda c: c["DetailsKinds"]["attributes"]["by_summary"].update({"range": "BlockHint"}),
         "DetailsKinds (DetailsKinds).by_summary: the shape does not take BlockHint"),
    ],
)  # fmt: skip
def test_a_seeded_system_side_difference_fails(tmp_path: Path, edit, expected: str) -> None:
    found = profile_differences(edited_system(tmp_path, edit))
    assert any(expected in f for f in found), found


def test_a_seeded_profile_side_difference_fails(system_view: SchemaView) -> None:
    extra = create_model("SourceProfile", __base__=P.SourceProfile, encoding_label=(str, None))
    found = profile_differences(system_view, {**PROFILE_PAIRS, "SourceProfile": extra})
    assert found == ["SourceProfile (SourceProfile): only the Pydantic shape has 'encoding_label'"]
    loose = create_model("ReferenceSpec", __base__=P.ReferenceSpec, render=(str, "browser"))
    found = profile_differences(system_view, {**PROFILE_PAIRS, "ReferenceSpec": loose})
    assert "ReferenceSpec (ReferenceSpec).render: the shape does not take ReferenceRender" in found
    optional = create_model("CorpusIndex", __base__=P.CorpusIndex, file=(str, ""))
    found = profile_differences(system_view, {**PROFILE_PAIRS, "CorpusIndex": optional})
    assert "CorpusIndex (CorpusIndex).file: required True vs False" in found


def test_the_parse_detail_payload_has_a_registry_entry() -> None:
    """O1's rendition write looks the payload schema up by kind and refuses without one."""
    from corpus_structure.schema import model, registry

    loaded = model.load()
    assert "parse_detail" not in registry.without_schema(loaded)
    (entry,) = [e for e in registry.payload_schema_entries(loaded) if e.kind == "parse_detail"]
    assert entry.class_ == "sys:ParseDetail"
