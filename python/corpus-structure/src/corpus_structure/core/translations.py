"""The declared translations whose types live in `core`, and their completeness harness.

Target model §7; foundations §3.5 (F2e, DP-08). Each translation is an ordinary function with a
declared source and target; the function is its owner's (T1: `validate` and the quote cascade;
T2: `validate`'s batch adapter, S2), the declarations and the target types are here. A declaration
maps every slot of each source class, in the source form, to the target field(s) it fills or
declares it omitted with the reason, and names the target fields the translation introduces. So a
slot added to the model and forgotten by a translation fails `completeness` before any data is
lost ("none silent", TM §7), and an `outside` item cannot disappear between a stored batch and the
keyed candidate set.

`completeness(translation, slots)` takes the source slots from the caller (the model's slot lists
through `SchemaView`, with `ci:form`), because `core` reads no model file.
"""

from __future__ import annotations

from collections.abc import Callable, Iterable, Mapping
from dataclasses import dataclass, field

from pydantic import BaseModel

from corpus_structure.core import batch as B
from corpus_structure.core import candidates as C
from corpus_structure.core import values as V


@dataclass(frozen=True)
class Omitted:
    """A source slot the translation drops on purpose, with why."""

    reason: str


type Image = str | tuple[str, ...] | Omitted  # the target field(s) a source slot fills


@dataclass(frozen=True)
class ClassMap:
    """One source class (a model class, in the translation's source form) into one target type."""

    source: str
    target: type[BaseModel]
    slots: Mapping[str, Image]
    introduced: Mapping[str, str] = field(default_factory=dict)  # target field -> what fills it


@dataclass(frozen=True)
class Translation:
    id: str
    name: str
    owner: str
    source_form: str  # the model's `ci:form` of the source: "model" (authored) or "stored"
    classes: tuple[ClassMap, ...]


def completeness(
    translation: Translation, slots: Callable[[str, str], Iterable[str]]
) -> list[str]:
    """Every gap of a declaration: a source slot neither mapped nor declared omitted, a declared
    slot the source lacks, a target field that does not exist, and a target field no source slot
    fills and the translation does not introduce. `slots(class, form)` lists the model's slots of
    a class in a form."""
    problems: list[str] = []
    for m in translation.classes:
        where = f"{translation.id} {m.source} -> {m.target.__name__}"
        source = set(slots(m.source, translation.source_form))
        for name in sorted(source - set(m.slots)):
            problems.append(f"{where}: {name!r} is neither mapped nor declared omitted")
        for name in sorted(set(m.slots) - source):
            problems.append(f"{where}: {name!r} is no slot of the source")
        filled: set[str] = set(m.introduced)
        for image in m.slots.values():
            if isinstance(image, Omitted):
                continue
            filled |= {image} if isinstance(image, str) else set(image)
        fields = set(m.target.model_fields)
        for name in sorted(filled - fields):
            problems.append(f"{where}: target field {name!r} does not exist")
        for name in sorted(fields - filled):
            problems.append(f"{where}: target field {name!r} is filled by nothing declared")
    return problems


def _same(*names: str) -> dict[str, Image]:
    return {n: n for n in names}


_LOCATED = "the quote cascade's located span"
_SPAN = {"start": _LOCATED, "end": _LOCATED, "coarse": "the cascade, when the quote is unlocated"}
_BY_SPAN = Omitted("replaced by the located span (start, end) on the rendition")

T1 = Translation(
    id="T1",
    name="authored -> stored",
    owner="validate (names, checks); methods.llm.parse (the quote cascade)",
    source_form="model",
    classes=(
        ClassMap("Batch", B.StoredBatch,
                 _same("unit_ref", "entities", "statements", "claims", "alternatives",
                       "unsupported"),
                 {"rendition": "the rendition the frame resolved on"}),
        ClassMap("EntityItem", B.StoredEntity,
                 _same("local_ref", "type", "label", "scope", "extent", "symbol", "aliases",
                       "identity"),
                 {"scope_segment": "the segment the local entity's extent resolves to"}),
        ClassMap("StatementItem", B.StoredStatement, _same("local_ref", "kind", "anchor")),
        ClassMap("OutsideItem", B.StoredOutside, _same("local_ref", "anchor", "descriptor")),
        ClassMap("ReferenceDescriptor", B.StoredDescriptor,
                 {"sentence": _BY_SPAN, "quote": _BY_SPAN, "target": "target"}, _SPAN),
        ClassMap("ClaimItem", B.StoredClaim,
                 _same("local_ref", "predicate", "subject", "statement", "statement_role",
                       "object", "qualifiers", "evidence", "establishment", "derived_from",
                       "rule")),
        ClassMap("Evidence", B.StoredEvidence,
                 {"sentence": _BY_SPAN, "quote": _BY_SPAN, "role": "role"}, _SPAN),
        ClassMap("AlternativeItem", B.AlternativeItem, _same("refs", "reason")),
        ClassMap("UnsupportedItem", B.StoredUnsupported,
                 {"local_ref": "local_ref", "reason": "reason", "sentence": _BY_SPAN,
                  "quote": _BY_SPAN}, _SPAN),
        ClassMap("PhraseValue", V.StoredPhrase,
                 {"t": "t", "text": "text", "sentence": _BY_SPAN}, _SPAN),
    ),
)  # fmt: skip

_KEY = {"key": "UNKEYED at submission; the key once keyed"}

T2 = Translation(
    id="T2",
    name="stored -> keyed candidate set",
    owner="validate (S2's batch adapter)",
    source_form="stored",
    classes=(
        ClassMap("Batch", C.KeyedCandidateSet,
                 {"unit_ref": Omitted("the unit is the holding record's (kb.observation); every "
                                      "item carries its own segments and spans"),
                  "rendition": "rendition", "entities": "entities",
                  # an outside item becomes an ExternalReference node, never a statement
                  "statements": ("statements", "references"), "claims": "claims",
                  "alternatives": "alternatives", "unsupported": "unsupported"}),
        ClassMap("EntityItem", C.CandidateEntity,
                 {"local_ref": "id", **_same("type", "label", "scope", "extent", "symbol",
                                             "aliases", "identity", "scope_segment")}, _KEY),
        ClassMap("StatementItem", C.CandidateStatement,
                 {"local_ref": "id", "kind": "kind", "anchor": "anchor"}, _KEY),
        ClassMap("OutsideItem", C.CandidateReference,
                 {"local_ref": "id", "descriptor": "descriptor",
                  "anchor": Omitted("the literal outside, which the node's type states")},
                 {**_KEY, "resolved_to": "AWAITING until consolidation resolves it"}),
        ClassMap("ClaimItem", C.CandidateClaim,
                 {"local_ref": "id", **_same("predicate", "subject", "statement",
                                             "statement_role", "object", "qualifiers",
                                             "evidence", "establishment", "derived_from",
                                             "rule")}, _KEY),
        ClassMap("AlternativeItem", C.CandidateAlternative, _same("refs", "reason")),
        ClassMap("UnsupportedItem", C.CandidateUnsupported,
                 {"local_ref": "id", **_same("reason", "start", "end", "coarse")}),
    ),
)  # fmt: skip

TRANSLATIONS: tuple[Translation, ...] = (T1, T2)
