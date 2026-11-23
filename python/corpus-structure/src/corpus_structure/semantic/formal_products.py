"""Source-native positioned formal production, separate from execution custody.

The released characterization classes own constituent shapes. This profile reuses the
actual nomination/parser/reducer and graph validators, with source identity established
before extraction rather than rewriting task-keyed reports after extraction.
"""

from __future__ import annotations

import json
from collections.abc import Callable, Mapping
from dataclasses import dataclass, field, replace
from functools import cached_property, lru_cache
from hashlib import sha256
from pathlib import Path
from typing import TYPE_CHECKING, Any, ClassVar

import yaml
from pydantic import BaseModel, ConfigDict, Field

from corpus_structure.core.evidence import MacroDef
from corpus_structure.methods.math import grammar as math_grammar
from corpus_structure.semantic.characterization import validate_inventory_topology
from corpus_structure.semantic.formal_evidence import FAMILIES
from corpus_structure.semantic.source_products import (
    native_selector_covers_extent,
    native_selector_facts,
)

from .characterization import (
    occurrence_identity_runtime,
    occurrence_identity_runtime_artifact,
    verify_inventory_literal_extents,
    verify_inventory_native_scores,
    verify_inventory_occurrence_ids,
)
from .characterization_evidence import validate_formal_normalization, validate_formal_positions
from .characterization_manifests import analytical_packets, append_manifest, manifest_contract
from .data_operation_json import canonical_json_bytes
from .data_operation_model import EffectiveDataOperationModel, EffectiveOperation, SubjectContext
from .data_operation_outcomes import successful_return_outcome
from .formal_evidence import (
    FormalIdentity,
    _LayerBuilder,
    extract_formal_facts,
    grammar_identity,
)
from .identity import canonical_bytes
from .native_source_view import freeze_native
from .python_operation_sources import PythonSourceCollection
from .source_products import (
    FrozenNativeSource as FrozenFormalSource,
)
from .source_products import (
    source_product_inputs,
    source_subject,
)
from .types import PreparedRelease, SourceArtifact, SourceBundle

if TYPE_CHECKING:
    from .data_operation_admission import PreparedCapabilityIdentity
    from .data_operation_bindings import BindingResult
    from .data_operation_ports import PortCompletion, PythonRoleValue

_MODEL = Path(__file__).resolve().parents[1] / "model/semantic/data-operation-characterization.yaml"
_INVENTORIES = (
    ("occurrences", "occurrence"),
    ("annotations", "annotation"),
    ("memberships", "membership"),
    ("terms", "term"),
    ("choices", "choice"),
)

_MEMBER_VARIANTS = (*_INVENTORIES, ("choice_members", "choice_member"))


def formal_product_inputs(
    bundle: SourceBundle, *, model_content: bytes | None = None
) -> SourceBundle:
    """Acquire the nominal profile alongside its reused released constituent types."""
    bundle = source_product_inputs(bundle)
    reserved = {"data_operation_characterization", "data_operation_characterization_root"}
    if reserved & {source.name for source in bundle.sources}:
        raise ValueError("formal profile schema uses reserved trusted names")
    content = _MODEL.read_bytes() if model_content is None else model_content
    root = "data_operation_characterization_root"
    return SourceBundle(
        root,
        (
            *bundle.sources,
            SourceArtifact("data_operation_characterization", content),
            SourceArtifact(
                root,
                yaml.safe_dump(
                    {
                        "id": "urn:corpus:data-operation-characterization-root",
                        "name": root,
                        "imports": [bundle.root, "data_operation_characterization"],
                    }
                ).encode(),
            ),
        ),
    )


def _values(model: BaseModel) -> dict[str, Any]:
    return model.model_dump(mode="json", exclude_unset=True)


@dataclass(frozen=True)
class _RecognizerSource:
    text: str
    pieces: tuple[dict[str, Any], ...]
    items: tuple[dict[str, Any], ...]
    health: dict[str, Any]
    native: Any

    def native_gap(self, start: int, end: int) -> bool:
        return self.native.native_gap(start, end)


class FormalEvidenceOptions(BaseModel):
    """Execution limits/macros are recipe custody, never product identity salt."""

    model_config = ConfigDict(frozen=True, extra="forbid")
    math_start: math_grammar.Kind = "any_value"
    parse_seconds: float = Field(default=math_grammar.PARSE_SECONDS, gt=0)
    max_forest_nodes: int = Field(default=20000, ge=1)
    max_inline_chars: int = Field(default=2048, ge=1)
    macros: dict[str, MacroDef] = Field(default_factory=dict)


@dataclass(frozen=True)
class _FormalPayload:
    content: bytes
    value: Mapping[str, Any]
    meaning: bytes
    members: tuple[bytes, ...]
    body_digest: str
    kind_contract: str


@dataclass(frozen=True, init=False)
class FormalEvidenceProduct:
    """Acquired formal evidence and its exact source, with separately bound placement."""

    prepared: PreparedRelease
    model: EffectiveDataOperationModel
    subject_context: SubjectContext | None
    _payload: ClassVar[_FormalPayload]
    _source: ClassVar[FrozenFormalSource]

    def __init__(self, *args, **kwargs):
        raise TypeError("formal evidence requires validated production or exact native acquisition")

    @classmethod
    def _from_payload(cls, payload, source, prepared, model, subject_context):
        product = object.__new__(cls)
        object.__setattr__(product, "_payload", payload)
        object.__setattr__(product, "_source", source)
        object.__setattr__(product, "prepared", prepared)
        object.__setattr__(product, "model", model)
        object.__setattr__(product, "subject_context", subject_context)
        return product

    @classmethod
    def _accept_checked(cls, typed, checked, source, prepared, model, subject_context):
        from .data_operation_identity import body_identity
        from .data_operation_ports import project_product_members
        from .data_operation_values import semantic_value

        kind = prepared.index.definitions["DdoFormalProduct"].iri
        contract = next(
            identity.key
            for identity in model.identities
            if (identity.owner, identity.domain) == (kind, "kind")
        )
        meaning = typed.model_dump(mode="python", exclude_unset=True)
        payload = _FormalPayload(
            canonical_bytes(checked),
            freeze_native(checked),
            canonical_bytes(semantic_value(meaning)),
            project_product_members(model, kind, meaning),
            body_identity(meaning).key,
            contract,
        )
        return cls._from_payload(payload, source, prepared, model, subject_context)

    def _require_acquired(self):
        if type(self) is not FormalEvidenceProduct or "_payload" not in vars(self):
            raise TypeError("formal evidence lacks its acquired payload")

    def __deepcopy__(self, memo):
        self._require_acquired()
        return self

    def with_context(self, context: SubjectContext | None) -> FormalEvidenceProduct:
        self._require_acquired()
        return self._from_payload(self._payload, self._source, self.prepared, self.model, context)

    @property
    def content(self) -> bytes:
        return self._payload.content

    @property
    def value(self) -> Mapping[str, Any]:
        return self._payload.value

    def _publication_context(self):
        if self.subject_context is None:
            raise ValueError(
                "native product identity requires an explicit acquired subject context"
            )
        return self.subject_context

    def require_readable_from(self, source, *, prepared=None, model=None):
        self._require_acquired()
        FrozenFormalSource._require_acquired(source)
        selected = source.value
        if self.value["source"] != selected["source"]:
            raise ValueError("formal construction input belongs to another original source")
        # The formal product owns its original selectors. Consumers can use different
        # selectors over the same captured source facts without relabelling that coverage.
        original = self._source.value
        if any(
            original.get(field) != selected.get(field)
            for field in ("text", "pieces", "items", "ancestors")
        ):
            raise ValueError("formal construction input differs from its acquired source facts")
        if model is not None:
            kind = (prepared or self.prepared).index.definitions["DdoFormalProduct"].iri
            if not any(
                (identity.owner, identity.domain, identity.key)
                == (kind, "kind", self._payload.kind_contract)
                for identity in model.identities
            ):
                raise ValueError("formal construction input has another nominal contract")

    @cached_property
    def semantic_id(self) -> str:
        from .data_operation_identity import contextual_product_identity

        return contextual_product_identity(
            kind=self._payload.kind_contract,
            context=self._publication_context(),
            body=self._payload.body_digest,
        ).key

    @cached_property
    def _inventory(self) -> Mapping[str, Any]:
        return formal_product_inventory(self.value)

    def inventory(self) -> Mapping[str, Any]:
        return self._inventory


def formal_product_inventory(body: Mapping[str, Any]) -> Mapping[str, Any]:
    """Project a formal body for analysis without granting publication authority."""
    result = {name: [] for name, _ in _INVENTORIES}
    by_kind = {kind: name for name, kind in _INVENTORIES}
    for packet in body["members"]:
        kind = packet["body"]["record_type"]
        if kind in by_kind:
            result[by_kind[kind]].append(packet["body"])
    return freeze_native({**result, "roles": [], "coverage": body["coverage"]})


def verify_formal_literal_geometry(text, pieces, members, lexicon):
    """Check literal observations and native-piece containment against selected source."""
    for packet in members:
        body = packet["body"]
        if body["record_type"] != "occurrence":
            continue
        for extent in body["extents"]:
            if "start" not in extent:
                continue
            if "end" not in extent:
                raise ValueError("formal occurrence differs from original literal slice")
            start, end = extent["start"], extent["end"]
            if (
                not 0 <= start < end <= len(text)
                or "text" not in extent
                or extent["text"] != text[start:end]
            ):
                raise ValueError("formal occurrence differs from original literal slice")
            # The authenticated source pieces partition the text in position
            # order. Locate the one piece whose exclusive end contains this span.
            lower, upper = 0, len(pieces)
            while lower < upper:
                item = (lower + upper) // 2
                if pieces[item]["end"] < end:
                    lower = item + 1
                else:
                    upper = item
            if lower == len(pieces):
                raise ValueError("formal occurrence escapes its original native piece")
            piece = pieces[lower]
            if (
                piece["start"] > start
                or piece["kind"] != "native_text"
                or piece["item_ref"] != extent["native_pointer"]
            ):
                raise ValueError("formal occurrence escapes its original native piece")
    for region in lexicon:
        for terminal in region["terminals"]:
            if terminal["text"] != text[terminal["start"] : terminal["end"]]:
                raise ValueError(
                    "primary lexical observation differs from its original unprotected slice"
                )


def verify_formal_member_local_addresses(packets):
    """Check local member addresses and build the validated inventory indexes."""
    data = {name: [] for name, _ in _INVENTORIES}
    data["roles"] = []
    names = {kind: name for name, kind in _INVENTORIES}
    seen = set()
    for packet in packets:
        body = packet["body"]
        local_id = body["local_id"]
        if packet["member_id"] != local_id:
            raise ValueError("formal packet differs from original semantic source/member")
        if local_id in seen:
            raise ValueError("formal packet repeats member identity")
        seen |= {local_id}
        if body["record_type"] != "choice_member":
            data[names[body["record_type"]]] += [body]
    indexes = {name: {row["local_id"]: row for row in data[name]} for name in data}
    all_nodes = {key: indexes[name][key] for name in indexes for key in indexes[name]}
    choices = {}
    for group in data["choices"]:
        for member in group["members"]:
            if member["local_id"] in all_nodes:
                raise ValueError("formal choice member repeats local identity")
            all_nodes[member["local_id"]] = member
            choices[member["local_id"]] = group
    return data, indexes, all_nodes, choices


def verify_formal_inventory_topology(packets):
    """Check exact closed member topology and return the checked inventory indexes."""
    data, indexes, all_nodes, choices = verify_formal_member_local_addresses(packets)
    validate_inventory_topology(data, indexes, all_nodes, choices)
    return data, indexes


def verify_formal_family_roster(coverage):
    """Require every declared formal family in its canonical order."""
    if tuple(row["family"] for row in coverage) != FAMILIES:
        raise ValueError("formal product must retain every examined family outcome")


def verify_formal_packed_members(packets):
    """Check that each projected packed alternative is exactly its group member."""
    expected = {
        member["local_id"]: {"record_type": "choice_member", "group_id": body["local_id"], **member}
        for packet in packets
        if (body := packet["body"])["record_type"] == "choice"
        for member in body["members"]
    }
    actual = {
        packet["member_id"]: packet["body"]
        for packet in packets
        if packet["body"]["record_type"] == "choice_member"
    }
    if actual != expected:
        raise ValueError(
            "formal alternative member projection differs from its owning packed group"
        )


def verify_formal_examined_scope(product, source):
    """Check examined scope and family coverage against the actual selected source."""
    selectors = source["selectors"]
    if product["source"] != source["source"] or tuple(product["selectors"]) != tuple(selectors):
        raise ValueError("formal product differs from exact selected source/scope")
    regions = product["lexicon"]
    for selector in selectors:
        if not any(region["selector"] == selector for region in regions):
            raise ValueError("primary lexicon does not retain every examined selector")
    for region in regions:
        selector = region["selector"]
        start, end = region["start"], region["end"]
        if (
            selector not in selectors
            or not 0 <= start <= end <= len(source["text"])
            or ("start" in selector and start < selector["start"])
            or ("end" in selector and end > selector["end"])
        ):
            raise ValueError("primary lexicon differs from exact examined region")
    for row in product["coverage"]:
        if tuple(row["eligible"]) != tuple(selectors) or tuple(row["examined"]) != tuple(selectors):
            raise ValueError("formal coverage differs from original examined scope")
        if product["outcome"] == "complete" and row["outcome"] not in {"complete", "empty"}:
            raise ValueError("complete formal product contains incomplete family coverage")


def verify_formal_lexical_links(occurrences, lexicon):
    """Check each protected atom's exact inventory link and terminal separation."""
    for region in lexicon:
        start, end = region["start"], region["end"]
        atoms, terminals = region["atoms"], region["terminals"]
        for atom in atoms:
            key = atom["occurrence"]
            if key not in occurrences or not start <= atom["start"] < atom["end"] <= end:
                raise ValueError("primary lexical protection has no exact retained occurrence")
            extents = occurrences[key]["extents"]
            if (
                any("start" not in extent or "end" not in extent for extent in extents)
                or min(e["start"] for e in extents) != atom["start"]
                or max(e["end"] for e in extents) != atom["end"]
            ):
                raise ValueError("primary lexical protection changes its retained occurrence")
        for terminal in terminals:
            if not start <= terminal["start"] < terminal["end"] <= end or any(
                atom["start"] < terminal["end"] and terminal["start"] < atom["end"]
                for atom in atoms
            ):
                raise ValueError(
                    "primary lexical observation differs from its original unprotected slice"
                )
        if region["availability"] != "available" and (atoms or terminals):
            raise ValueError("unsupported primary lexicon cannot assert characterized terminals")


def verify_formal_occurrence_origin(occurrences, selected):
    """Check actual original atoms, pages and selected ranges for occurrence extents."""
    parents, pages = native_selector_facts(selected["items"], selected["ancestors"])
    projection = selected["source"]["projection"]
    text_length = len(selected["text"])
    for occurrence in occurrences:
        for extent in occurrence["extents"]:
            pointer = extent["native_pointer"]
            if pointer not in pages:
                raise ValueError("formal occurrence has no original native atom")
            if "page" in extent and pages[pointer] != {extent["page"]}:
                raise ValueError("formal occurrence has another original page")
            if extent["projection"] != projection:
                raise ValueError("formal occurrence has another original projection")
            if "start" in extent and not native_selector_covers_extent(
                parents, pages, selected["selectors"], extent, text_length
            ):
                raise ValueError("formal occurrence escapes the selected examined scope")


def validate_formal_product(
    prepared: PreparedRelease,
    value: Mapping[str, Any],
    source: FrozenFormalSource,
    *,
    model: EffectiveDataOperationModel,
    subject_context: SubjectContext | None = None,
) -> FormalEvidenceProduct:
    typed = prepared.validate_json("DdoFormalProduct", canonical_bytes(value))
    checked = _values(typed)
    selected = source.value
    member_contracts = formal_member_contracts(prepared, model)
    packets = analytical_packets(checked, member_contracts["manifest"])
    verify_formal_examined_scope(checked, selected)
    data, indexes = verify_formal_inventory_topology(packets)
    subject = source_subject(checked["source"])
    context = dict(
        subject=subject,
        subject_definition="original-source-view",
        original_source=checked["source"]["document"],
        analyzed_scope=dict(source=checked["source"], selectors=list(selected["selectors"])),
    )
    for packet in packets:
        if packet["kind_contract"] != member_contracts[packet["body"]["record_type"]]:
            raise ValueError("formal packet has another admitted nominal member contract")
        if packet["context"] != context:
            raise ValueError("formal packet differs from original semantic source/member")
    verify_formal_packed_members(packets)
    verify_formal_literal_geometry(
        selected["text"], selected["pieces"], packets, checked["lexicon"]
    )
    verify_inventory_occurrence_ids(checked)
    verify_formal_occurrence_origin(data["occurrences"], selected)
    verify_formal_lexical_links(indexes["occurrences"], checked["lexicon"])
    validate_formal_positions(indexes)
    validate_formal_normalization(indexes["annotations"])
    verify_inventory_literal_extents(data["occurrences"])
    verify_inventory_native_scores(packets)
    verify_formal_family_roster(checked["coverage"])
    return FormalEvidenceProduct._accept_checked(
        typed, checked, source, prepared, model, subject_context
    )


def acquired_formal_product(
    prepared, value, source, *, model, subject_context, member
) -> FormalEvidenceProduct:
    """Decode an exact whole formal product whose consumer's rules were bound natively."""
    from .data_operation_model import BoundRoleMember
    from .enriched_document_products import acquire_characterization_payload

    if type(member) is not BoundRoleMember or member.member is not None:
        raise ValueError("selected formal evidence requires its exact whole binding member")
    definition = prepared.index.definitions["DdoFormalProduct"]
    kind_contract = next(
        identity.key
        for identity in model.identities
        if (identity.owner, identity.domain) == (definition.iri, "kind")
    )
    admitted = acquire_characterization_payload(
        canonical_bytes(value), prepared, model, definition, ()
    )
    selected = source.value
    payload = _FormalPayload(
        admitted.content,
        admitted.value,
        admitted.meaning,
        admitted.members,
        admitted.body_digest,
        kind_contract,
    )
    product = FormalEvidenceProduct._from_payload(payload, source, prepared, model, subject_context)
    if (
        kind_contract != member.kind_contract
        or product.semantic_id != member.product
        or product.value["source"] != selected["source"]
        or tuple(product.value["selectors"]) != tuple(selected["selectors"])
    ):
        raise ValueError("formal body differs from its exact selected native product/source")
    return product


@dataclass(frozen=True)
class PreparedFormalEvidence:
    """Explicit acquired grammar/schema capability; no Reader, selection or GPU access."""

    prepared: PreparedRelease
    grammar: str
    model: EffectiveDataOperationModel

    def run(
        self,
        source: FrozenFormalSource,
        options: FormalEvidenceOptions,
        *,
        check_active: Callable[[], None] = lambda: None,
        subject_context: SubjectContext | None = None,
    ) -> FormalEvidenceProduct:
        # Revalidate owned boundary bytes; model_construct/hand-created wrappers are not authority.
        source = FrozenFormalSource.acquire(self.prepared, source)
        options = FormalEvidenceOptions.model_validate(options.model_dump(mode="python"))
        if self.grammar != grammar_identity():
            raise ValueError("formal capability differs from acquired effective grammar assets")
        value = formal_product_values(
            source,
            options,
            formal_member_contracts(self.prepared, self.model),
            check_active=check_active,
        )
        return validate_formal_product(
            self.prepared, value, source, model=self.model, subject_context=subject_context
        )


def formal_member_contracts(
    prepared: PreparedRelease, model: EffectiveDataOperationModel
) -> dict[str, str]:
    """Use the admitted packet variants' nominal body graph, never guessed kind names."""
    identities = {(item.owner, item.domain): item.key for item in model.identities}
    result = {}
    for definition in prepared.definitions:
        if "DdoFormalMember" not in definition.ancestors or definition.abstract:
            continue
        discriminator = next(
            prop.equals_string for prop in definition.properties if prop.name == "record_type"
        )
        if discriminator == "manifest":
            continue
        if discriminator is None or discriminator in result:
            raise ValueError("formal packet variants require unique declared kind correspondence")
        result[discriminator] = identities[definition.iri, "kind"]
    if set(result) != {kind for _, kind in _MEMBER_VARIANTS}:
        raise ValueError("formal member contracts differ from the actual produced inventories")
    result["manifest"] = manifest_contract(prepared, model, "DdoFormalManifest")
    return result


def formal_positioned_lexicon(builder, selected):
    """Primary categories outside whole original atoms and positioned formal fields."""
    from .constructions.lexical import ProtectedAtom, classify

    occurrences = builder.occurrences
    protected = []
    for annotation in builder.annotations:
        if "formal_input" not in annotation or annotation["family"] == "formal.lexical":
            continue
        parent = annotation["formal_input"]["parent_occurrence"]
        for extent in occurrences[parent]["extents"]:
            if "start" in extent and extent["start"] < extent["end"]:
                protected.append((extent["start"], extent["end"], parent))
    for piece in builder.view.pieces:
        if piece["kind"] == "native_text" and builder.items.get(piece["item_ref"], {}).get(
            "label"
        ) in {"formula", "reference", "reference_marker"}:
            protected.append(
                (
                    piece["start"],
                    piece["end"],
                    builder.occurrence(piece, piece["start"], piece["end"]),
                )
            )
    protected = sorted(set(protected))
    protected = [
        (a, b, o)
        for a, b, o in protected
        if not any(c <= a and b <= d and (a, b) != (c, d) for c, d, _ in protected)
    ]
    if any(a < c < b < d for a, b, _ in protected for c, d, _ in protected):
        raise ValueError("primary formal protection has crossing original atoms")
    result = []
    for selector in selected:
        lower, upper = selector.get("start", 0), selector.get("end", len(builder.view.text))
        admitted = []
        for piece in builder.view.pieces:
            if piece["kind"] != "native_text":
                continue
            if builder.selector_match(selector, piece["item_ref"]) is not True:
                continue
            a, b = max(lower, piece["start"]), min(upper, piece["end"])
            if a < b:
                if admitted and builder.view.native_gap(admitted[-1][1], a):
                    admitted[-1] = (admitted[-1][0], b)
                else:
                    admitted.append((a, b))
        if not admitted:
            admitted = [(lower, lower)]
        for start, end in admitted:
            intervals = [(a, b, o) for a, b, o in protected if start <= a < b <= end]
            if any(a < end and start < b and not start <= a < b <= end for a, b, _ in protected):
                result.append(
                    dict(
                        selector=dict(selector),
                        start=start,
                        end=end,
                        availability="unsupported",
                        reason="selected source cuts a protected original atom",
                        atoms=[],
                        terminals=[],
                    )
                )
                continue
            atoms = tuple(ProtectedAtom(a - start, b - start, o) for a, b, o in intervals)
            terminals = classify(builder.view.text[start:end], atoms)
            result.append(
                dict(
                    selector=dict(selector),
                    start=start,
                    end=end,
                    availability="available",
                    atoms=[dict(start=a, end=b, occurrence=o) for a, b, o in intervals],
                    terminals=[
                        dict(
                            terminal=row.terminal,
                            start=row.start + start,
                            end=row.end + start,
                            text=row.text,
                        )
                        for row in terminals
                    ],
                )
            )
    return result


def formal_product_values(
    source: FrozenFormalSource,
    options: FormalEvidenceOptions,
    member_contracts: Mapping[str, str],
    *,
    check_active: Callable[[], None] = lambda: None,
) -> dict[str, Any]:
    """The one pure extraction/packet construction kernel over owned typed ingress.

    Private child transport is admitted by its parent; the parent validates the full
    nominal product before anything can become a PortCompletion/native intent.
    """
    selected = source.value
    coordinate = selected["source"]
    check_active()
    view = _RecognizerSource(
        selected["text"],
        tuple(selected["pieces"]),
        tuple((*selected["items"], *selected.get("ancestors", ()))),
        {"formula_outcomes": selected.get("recognition", [])},
        source.view,
    )
    builder = _LayerBuilder(
        view,
        {},
        FormalIdentity(
            canonical_bytes(coordinate), coordinate["projection"], source_subject(coordinate), True
        ),
        selector_match=source.selector_index().matches,
    )
    builder.macros = dict(options.macros)
    extract_formal_facts(
        builder,
        selected["selectors"],
        math_start=options.math_start,
        parse_seconds=options.parse_seconds,
        max_forest_nodes=options.max_forest_nodes,
        max_inline_chars=options.max_inline_chars,
        check_active=check_active,
    )
    lexicon = formal_positioned_lexicon(builder, selected["selectors"])
    coverage = [
        dict(
            family=family,
            eligible=selected["selectors"],
            examined=selected["selectors"],
            availability="available",
            outcome="partial"
            if builder.problems[family]
            else "complete"
            if builder.counts[family]
            else "empty",
            **(
                {"reason": "; ".join(dict.fromkeys(builder.problems[family]))}
                if builder.problems[family]
                else {}
            ),
        )
        for family in FAMILIES
    ]
    members = []
    records = {name: getattr(builder, name) for name, _ in _INVENTORIES}
    records["choice_members"] = [
        dict(group_id=group["local_id"], **member)
        for group in builder.choices.values()
        for member in group["members"]
    ]
    for inventory, kind in _MEMBER_VARIANTS:
        values = records[inventory]
        rows = values.values() if isinstance(values, dict) else values
        for row in rows:
            members.append(
                dict(
                    member_id=row["local_id"],
                    kind_contract=member_contracts[kind],
                    context=dict(
                        subject=source_subject(coordinate),
                        subject_definition="original-source-view",
                        original_source=coordinate["document"],
                        analyzed_scope=dict(source=coordinate, selectors=selected["selectors"]),
                    ),
                    body={"record_type": kind, **row},
                )
            )
    check_active()
    value = dict(
        source=coordinate,
        selectors=selected["selectors"],
        outcome="partial" if any(builder.problems.values()) else "complete",
        coverage=coverage,
        lexicon=lexicon,
        members=members,
    )

    return append_manifest(value, member_contracts["manifest"])


def prepare_formal_evidence(
    prepared: PreparedRelease, model: EffectiveDataOperationModel, *, grammar: str
) -> PreparedFormalEvidence:
    if grammar != grammar_identity():
        raise ValueError("formal profile requires explicitly acquired effective grammar assets")
    for name in ("DdoSelectedNativeSource", "DdoFormalProduct"):
        prepared.adapter(name)
    return PreparedFormalEvidence(prepared, grammar, model)


def execute_formal_profile(
    receiver, source: FrozenFormalSource, math_start: str = "any_value"
) -> FormalEvidenceProduct:
    """The original endpoint's explicitly captured prepared-resource boundary."""
    from corpus_structure.methods.formal_evidence import FormalEvidenceOperation

    if type(receiver) is not FormalEvidenceOperation:
        raise ValueError("formal execution requires its exact prepared receiver")
    options = FormalEvidenceOptions.model_validate(
        {**receiver.options.model_dump(mode="python"), "math_start": math_start}
    )
    return receiver.profile.run(source, options, check_active=receiver.check_active)


def formal_execution_custody() -> SourceArtifact:
    """Physical adapter/CPU/receipt code belongs to runtime custody, not recipe meaning."""
    root = Path(__file__).parent
    names = (
        "formal_products.py",
        "characterization_evidence.py",
        "source_products.py",
        "established_validity.py",
        "cpu_execution.py",
        "cpu_receipts.py",
    )
    return SourceArtifact(
        "formal/execution-custody",
        canonical_bytes(
            {
                "version": "formal-execution-custody-v1",
                "files": [(name, (root / name).read_bytes().hex()) for name in names],
            }
        ),
        runtime_transport=True,
    )


def _formal_asset_paths():
    root = Path(__file__).parents[1]
    return (
        ("sympy/grammar/latex.lark", math_grammar.SHIPPED),
        ("grammar-extension", math_grammar.EXTENSION),
        ("formal-members", _MODEL),
        ("characterization", root / "model/semantic/characterization.yaml"),
        ("data-operation-source", root / "model/semantic/data-operation-source.yaml"),
    )


def _formal_asset_entries():
    return (
        execute_formal_profile,
        PreparedFormalEvidence.run,
        extract_formal_facts,
        validate_formal_product,
    )


@lru_cache(maxsize=1)
def formal_profile_assets() -> SourceArtifact:
    """Capture formal production and the effective grammar assets it reads."""
    from .operation_code_assets import code_asset

    return code_asset("formal/profile-assets", _formal_asset_entries(), _formal_asset_paths())


def _formal_decimal_runtime() -> SourceArtifact:
    from .characterization_evidence import Decimal
    from .external_runtime import acquire_codec_runtime

    decimal = next(runtime for runtime in acquire_codec_runtime() if runtime.reference == "decimal")
    if dict(decimal.symbols)["decimal.Decimal"] is not Decimal:
        raise ValueError("formal numeric checker differs from the acquired decimal runtime")
    return SourceArtifact("formal/decimal-runtime", bytes.fromhex(decimal.digest))


def formal_operation_sources():
    """Capture the original endpoint plus its explicit immutable parser boundary."""
    from .observations import native_number_runtime_artifact
    from .python_operation_sources import PythonSource, PythonSourceCollection

    path = Path(__file__).parents[1] / "methods/formal_evidence.py"
    semantic = Path(__file__).parent
    return PythonSourceCollection(
        (
            PythonSource(
                "corpus_structure.semantic.formal_products",
                Path(__file__).read_bytes(),
                str(Path(__file__)),
            ),
            PythonSource(
                "corpus_structure.methods.formal_evidence",
                path.read_bytes(),
                str(path),
            ),
            *(
                PythonSource(
                    "corpus_structure.semantic." + module,
                    (semantic / (module + ".py")).read_bytes(),
                    str(semantic / (module + ".py")),
                )
                for module in (
                    "characterization",
                    "characterization_evidence",
                    "data_operation_json",
                    "formal_evidence",
                    "observations",
                    "source_products",
                )
            ),
        ),
        boundary_contracts=(
            formal_profile_assets(),
            formal_execution_custody(),
            _formal_decimal_runtime(),
            native_number_runtime_artifact(),
            occurrence_identity_runtime_artifact(),
        ),
    )


@dataclass(frozen=True)
class PreparedFormalEvidencePort:
    native_selections = ()

    """Admitted prepared implementation of the original source-native entrypoint."""

    identity: PreparedCapabilityIdentity
    operation: EffectiveOperation
    profile: PreparedFormalEvidence
    authorize: Callable[[PreparedCapabilityIdentity], None]
    custody: tuple[SourceArtifact, ...]
    sources: PythonSourceCollection | None = None
    _occurrence_runtime: tuple[Any, ...] = field(init=False, repr=False, compare=False)
    _verification: Any = field(init=False, repr=False, compare=False)
    _basis: tuple = field(init=False, repr=False, compare=False)
    _asset_paths: tuple = field(init=False, repr=False, compare=False)
    _assets_digest: str = field(init=False, repr=False, compare=False)
    _member_contracts: tuple[tuple[str, str], ...] = field(init=False, repr=False, compare=False)

    @property
    def logical_signature(self):
        import inspect

        return inspect.Signature(
            (
                inspect.Parameter(
                    "source", inspect.Parameter.POSITIONAL_OR_KEYWORD, annotation=FrozenFormalSource
                ),
                inspect.Parameter(
                    "math_start",
                    inspect.Parameter.POSITIONAL_OR_KEYWORD,
                    annotation=str,
                    default="any_value",
                ),
            ),
            return_annotation=FormalEvidenceProduct,
        )

    def __post_init__(self):
        from corpus_structure.methods import formal_evidence as endpoint

        from .data_operation_ports import PortRefusal
        from .data_operation_prepared_products import (
            authenticated_prepared_product,
            verify_prepared_product,
        )
        from .file_custody import verified_file
        from .operation_code_assets import code_asset_sources

        if endpoint.execute_formal_profile is not execute_formal_profile:
            raise PortRefusal("loaded formal resource bridge differs from acquired implementation")
        required = formal_operation_sources()
        sources = required if self.sources is None else self.sources
        functions = (
            (
                "corpus_structure.methods.formal_evidence.FormalEvidenceOperation.run",
                endpoint.FormalEvidenceOperation.run,
            ),
            (
                "corpus_structure.semantic.formal_products.execute_formal_profile",
                execute_formal_profile,
            ),
            (
                "corpus_structure.semantic.formal_products.PreparedFormalEvidence.run",
                self.profile.run.__func__,
            ),
            (
                "corpus_structure.semantic.formal_products.verify_formal_occurrence_origin",
                verify_formal_occurrence_origin,
            ),
            (
                "corpus_structure.semantic.characterization.verify_inventory_native_scores",
                verify_inventory_native_scores,
            ),
            (
                "corpus_structure.semantic.characterization.verify_inventory_occurrence_ids",
                verify_inventory_occurrence_ids,
            ),
            (
                "corpus_structure.semantic.data_operation_json.canonical_json_bytes",
                canonical_json_bytes,
            ),
            (
                "corpus_structure.semantic.formal_products.verify_formal_inventory_topology",
                verify_formal_inventory_topology,
            ),
            (
                "corpus_structure.semantic.formal_products.verify_formal_family_roster",
                verify_formal_family_roster,
            ),
            (
                "corpus_structure.semantic.formal_products.verify_formal_member_local_addresses",
                verify_formal_member_local_addresses,
            ),
            (
                "corpus_structure.semantic.source_products.native_selector_covers_extent",
                native_selector_covers_extent,
            ),
            (
                "corpus_structure.semantic.source_products.native_selector_facts",
                native_selector_facts,
            ),
            (
                "corpus_structure.semantic.formal_evidence.extract_formal_facts",
                extract_formal_facts,
            ),
            (
                "corpus_structure.semantic.characterization_evidence.validate_formal_normalization",
                validate_formal_normalization,
            ),
            (
                "corpus_structure.semantic.formal_products.PreparedFormalEvidencePort.__post_init__",
                type(self).__post_init__,
            ),
            (
                "corpus_structure.semantic.formal_products.PreparedFormalEvidencePort.plan_python",
                type(self).plan_python,
            ),
            (
                "corpus_structure.semantic.formal_products.PreparedFormalEvidencePort.invoke_python",
                type(self).invoke_python,
            ),
        )
        verify_prepared_product(
            self.identity,
            self.profile.model,
            self.operation,
            sources,
            self.custody,
            assets=required.boundary_contracts,
            functions=functions,
            authorize=self.authorize,
            required_sources=required,
        )
        member_contracts = tuple(
            formal_member_contracts(self.profile.prepared, self.profile.model).items()
        )
        verification = authenticated_prepared_product(sources, functions, required_sources=required)
        captured = {asset.name: asset for asset in required.boundary_contracts}
        profile_assets = captured["formal/profile-assets"]
        asset_paths = _formal_asset_paths()
        paths = dict(asset_paths)
        content = tuple(
            (paths[label], bytes.fromhex(encoded))
            for label, encoded in json.loads(profile_assets.content)["assets"]
        )
        content += tuple(
            (Path(__file__).parent / name, bytes.fromhex(encoded))
            for name, encoded in json.loads(captured["formal/execution-custody"].content)["files"]
        )
        files = {record.path.resolve(): record for record in verification.files}
        content += tuple(
            (Path(source.filename), source.content)
            for source in code_asset_sources(_formal_asset_entries()).sources
        )
        for path, encoded in content:
            record = verified_file(path, sha256(encoded).hexdigest())
            if (
                record.path.resolve() in files
                and files[record.path.resolve()].digest != record.digest
            ):
                raise PortRefusal("formal asset disagrees with captured source")
            files[record.path.resolve()] = record
        verification.files = tuple(files.values())
        object.__setattr__(self, "_occurrence_runtime", occurrence_identity_runtime())
        object.__setattr__(self, "_verification", verification)
        object.__setattr__(self, "_asset_paths", asset_paths)
        object.__setattr__(self, "_assets_digest", profile_assets.digest)
        object.__setattr__(self, "_member_contracts", member_contracts)
        object.__setattr__(
            self,
            "_basis",
            tuple(
                (name, getattr(self, name))
                for name in (
                    "_occurrence_runtime",
                    "identity",
                    "operation",
                    "profile",
                    "authorize",
                    "custody",
                    "sources",
                    "_verification",
                    "_asset_paths",
                    "_assets_digest",
                    "_member_contracts",
                )
            ),
        )

    def _verify(self) -> None:
        from .data_operation_ports import PortRefusal

        if any(getattr(self, name) is not value for name, value in self._basis):
            raise PortRefusal("formal port correspondence changed after acquisition")
        if _formal_asset_paths() != self._asset_paths:
            raise PortRefusal("formal resources differ from acquired asset locations")
        try:
            self._verification.check()
            for runtime in self._occurrence_runtime:
                runtime.check()
        except ValueError as error:
            raise PortRefusal(
                "formal resources differ from acquired custody/runtime slice: " + str(error)
            ) from error
        self.authorize(self.identity)

    def _source(self, values, binding):
        from .data_operation_ports import PortRefusal, PythonRoleValue
        from .data_operation_values import decode_semantic_value

        inputs = tuple(role for role in self.operation.roles if role.direction == "input")
        contracts = {(item.owner, item.domain): item.key for item in self.profile.model.identities}
        if len(values) != 1 or not isinstance(values[0], PythonRoleValue):
            raise PortRefusal("formal capability requires one typed selected-source role")
        value = values[0]
        if value.role != inputs[0].name or value.kind_contract != contracts[inputs[0].kind, "kind"]:
            raise PortRefusal("formal source role has another nominal contract")
        actual = value.value
        if isinstance(actual, FrozenFormalSource):
            source = FrozenFormalSource.acquire(self.profile.prepared, actual)
        elif isinstance(actual, BaseModel):
            source = FrozenFormalSource.acquire(self.profile.prepared, _values(actual))
        elif isinstance(actual, Mapping):
            source = FrozenFormalSource.acquire(self.profile.prepared, actual)
        else:
            raise PortRefusal("formal source ingress requires its explicit selected-source value")
        if binding is not None and (
            not binding.sufficient
            or binding.operation != self.operation.semantic_id
            or binding.subject != source_subject(source.value["source"])
            or set(decode_semantic_value(json.loads(binding.parameters))) != {"math_start"}
        ):
            raise PortRefusal("formal input differs from the frozen source binding")
        return source

    def _options(self, binding):
        from .data_operation_values import decode_semantic_value

        parameters = (
            {} if binding is None else decode_semantic_value(json.loads(binding.parameters))
        )
        return FormalEvidenceOptions.model_validate(parameters)

    def _completion(self, product, source, binding=None):
        if binding is not None:
            product = product.with_context(binding.subject_context)
        from ._data_operation_wire import WireKindContract, WireOutputMember
        from .data_operation_ports import PortCompletion, RoleValue
        from .established_validity import (
            RuleAttestationPreparation,
            RuleObservedInput,
        )

        output = next(role for role in self.operation.roles if role.direction == "output")
        contracts = {(item.owner, item.domain): item.key for item in self.profile.model.identities}
        kind_contract = contracts[output.kind, "kind"]
        meaning = product._payload.meaning
        members = product._payload.members
        attestations = ()
        if product.subject_context is not None:
            kind = next(
                item for item in self.profile.model.kinds if item.semantic_id == output.kind
            )
            packet: WireOutputMember = {
                "role": output.name,
                "position": 0,
                "multiplicity": 1,
                "product": {
                    "kind_contract": WireKindContract(kind_contract),
                    "body": json.loads(meaning),
                    "members": [json.loads(member) for member in members],
                },
            }
            # Both the direct producer and CPU result hydration ran the named
            # split validators against this exact output and selected source.
            selected = {"source": (RuleObservedInput(source.value),)}
            observed = {
                "text.formal_evidence/literal-source-geometry": selected,
                "text.formal_evidence/packed-choice-members": None,
                "text.formal_evidence/numeric-normalization": None,
                "text.formal_evidence/examined-scope": selected,
                "text.formal_evidence/occurrence-origin": selected,
                "text.formal_evidence/lexical-inventory-links": None,
                "text.formal_evidence/family-roster": None,
                "text.formal_evidence/member-local-addresses": None,
                "text.formal_evidence/inventory-topology": None,
                "text.formal_evidence/native-numeric-scores": None,
                "text.formal_evidence/canonical-occurrence-addresses": None,
                "text.formal_evidence/symbolic-inventory-positions": None,
            }
            preparation = RuleAttestationPreparation(
                kind, self.operation.semantic_id, packet, product.subject_context
            )
            attestations = tuple(
                preparation.attest(
                    rule,
                    selected_inputs=observed[rule.id],
                )
                for rule in self.profile.model.rules
                if rule.id in observed
            )
        return PortCompletion(
            self.operation.semantic_id,
            (
                RoleValue(
                    output.name,
                    kind_contract,
                    product.content,
                    meaning,
                    members,
                ),
            ),
            outcome=successful_return_outcome(self.operation),
            rule_attestations=attestations,
        )

    def invoke_python(
        self,
        values: tuple[PythonRoleValue, ...],
        *,
        binding: BindingResult | None = None,
        check_active: Callable[[], None] = lambda: None,
    ) -> PortCompletion:
        from corpus_structure.methods.formal_evidence import FormalEvidenceOperation

        # The actual math frontend owns process-main-thread SIGALRM deadlines.
        # Scheduler callers use plan_python to execute in the existing CPU owner.
        math_grammar.require_main_thread()
        self._verify()
        source = self._source(values, binding)
        options = self._options(binding)
        product = FormalEvidenceOperation(self.profile, options, check_active).run(
            source, math_start=options.math_start
        )
        self._verify()
        return self._completion(product, source, binding)

    def plan_python(self, values, *, binding=None, check_active=lambda: None, execution_owner):
        """Yield admitted source-native CPU work under the invocation's one pool/credit."""
        from corpus_structure.core.method import PreparedWork

        source = self._source(values, binding)
        cpu = execution_owner.cpu
        check_active()

        # Formal work carries its acquired source, member contracts and parser assets.
        # The process-owned pool can serve separately admitted release contexts.
        packet = canonical_bytes(
            dict(
                profile="formal-source-native",
                member_contracts=dict(self._member_contracts),
                source=source.content.decode(),
                options=self._options(binding).model_dump_json(),
                grammar=self.profile.grammar,
                assets=self._assets_digest,
            )
        )

        def submit():
            check_active()
            admission = cpu.try_admit(
                check_active, reservation=execution_owner.reservation, packet_bytes=len(packet)
            )
            if admission is None:
                return None
            try:
                self._verify()
                check_active()
                return cpu.submit_formal(admission, packet, check_active)
            except BaseException:
                if not admission.submitted:
                    cpu.release_admission(admission)
                raise

        (reply,) = yield (PreparedWork(submit),)
        check_active()
        self._verify()
        product = validate_formal_product(
            self.profile.prepared, json.loads(reply.content), source, model=self.profile.model
        )
        return replace(
            self._completion(product, source, binding),
            cpu_execution_evidence=canonical_bytes(reply.execution_receipt.record()),
        )


def resolve_formal_evidence_port(
    prepared: PreparedRelease,
    model: EffectiveDataOperationModel,
    operation: str,
    *,
    identity: PreparedCapabilityIdentity,
    authorize: Callable[[PreparedCapabilityIdentity], None],
    custody: tuple[SourceArtifact, ...],
    sources: PythonSourceCollection | None = None,
) -> PreparedFormalEvidencePort:
    from .data_operation_ports import PortRefusal

    selected = model.operation(operation)
    inputs = tuple(role for role in selected.roles if role.direction == "input")
    outputs = tuple(role for role in selected.roles if role.direction == "output")
    expected = prepared.index.definitions
    if (
        selected.capabilities.forms != ("scalar",)
        or selected.capabilities.preparation != "resource"
        or selected.capabilities.cancellation != "cooperative"
        or selected.capabilities.ownership != "immutable"
        or selected.effects
        or len(inputs) != 1
        or len(outputs) != 1
        or inputs[0].kind != expected["DdoSelectedNativeSource"].iri
        or outputs[0].kind != expected["DdoFormalProduct"].iri
        or inputs[0].parameter != "source"
    ):
        raise PortRefusal("operation does not establish the prepared formal profile")
    port = PreparedFormalEvidencePort(
        identity,
        selected,
        prepare_formal_evidence(prepared, model, grammar=grammar_identity()),
        authorize,
        custody,
        sources,
    )
    return port
