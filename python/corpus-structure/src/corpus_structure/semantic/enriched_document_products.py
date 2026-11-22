"""A combined document view preserving every original source coordinate and product."""

from __future__ import annotations

import json
from collections import defaultdict
from collections.abc import Mapping
from dataclasses import dataclass, field
from functools import cached_property
from hashlib import sha256
from typing import Any, ClassVar

from corpus_structure.caches import declare

from .characterization import characterization_profiles
from .data_operation_identity import body_identity, contextual_product_identity
from .data_operation_model import EffectiveDataOperationModel, SubjectContext
from .data_operation_partitions import partition_header
from .data_operation_source_sets import FrozenSourceSet, SelectedSourceSetEntry
from .data_product_reference import DataProductMemberReference, DataProductReference
from .identity import canonical_bytes
from .native_source_view import freeze_native, thaw_native
from .source_products import FrozenNativeSource
from .types import PreparedRelease


@dataclass(frozen=True)
class _CharacterizationPayload:
    content: bytes
    value: Mapping[str, Any]
    meaning: bytes
    members: tuple[bytes, ...]
    body_digest: str


@declare(
    "characterization-product-payloads",
    "runtime_bytes",
    key=lambda content, prepared, model, definition, collections: (
        sha256(content).digest(),
        prepared.release_id,
        sha256(model.content).digest(),
        definition.iri,
        collections,
    ),
    weight=lambda payload: (
        len(payload.content) + len(payload.meaning) + sum(map(len, payload.members))
    ),
)
def _characterization_payload(content, prepared, model, definition, collections):
    from .data_operation_ports import project_product_members
    from .data_operation_values import semantic_value

    committed = json.loads(content) if collections else None
    if committed is not None:
        header = {name: value for name, value in committed.items() if name not in collections}
        checked = prepared.validate_json(definition.name, canonical_bytes(header))
    else:
        checked = prepared.validate_json(definition.name, content)
    typed = checked.model_dump(mode="python", exclude_unset=True)
    display = checked.model_dump(mode="json", exclude_unset=True)
    if committed is not None:
        typed.update({name: committed[name] for name in collections})
        display = committed
    return _CharacterizationPayload(
        content if collections else canonical_bytes(display),
        freeze_native(display),
        canonical_bytes(semantic_value(typed)),
        project_product_members(model, definition.iri, typed),
        body_identity(committed if committed is not None else typed).key,
    )


@dataclass(frozen=True, init=False)
class RetainedCharacterizationProduct:
    """An actual concrete nominal kind under the declared characterization marker."""

    content: bytes
    prepared: PreparedRelease
    model: EffectiveDataOperationModel
    kind: str
    subject_context: SubjectContext | None
    selected_product: str | None
    selected_member: str | None
    partitions: tuple[bytes, ...] | None
    _payload: ClassVar[_CharacterizationPayload]

    def __init__(self, *args, **kwargs):
        raise TypeError("retained characterization requires validating acquisition")

    @classmethod
    def _from_payload(
        cls, payload, prepared, model, kind, context, partitions, selection=(None, None)
    ):
        result = object.__new__(cls)
        object.__setattr__(result, "content", payload.content)
        object.__setattr__(result, "_payload", payload)
        object.__setattr__(result, "prepared", prepared)
        object.__setattr__(result, "model", model)
        object.__setattr__(result, "kind", kind)
        object.__setattr__(result, "subject_context", context)
        object.__setattr__(result, "partitions", partitions)
        object.__setattr__(result, "selected_product", selection[0])
        object.__setattr__(result, "selected_member", selection[1])
        return result

    @classmethod
    def acquire(cls, prepared, model, kind, content, *, subject_context=None, partitions=None):
        if type(content) is not bytes or (
            partitions is not None
            and (
                type(partitions) is not tuple
                or any(type(packet) is not bytes for packet in partitions)
            )
        ):
            raise TypeError("retained characterization requires immutable body and packet bytes")
        definition = prepared.index.by_iri.get(kind)
        if (
            definition is None
            or definition.abstract
            or "DdoCharacterizationEnvelope" not in definition.ancestors
        ):
            raise ValueError("view input lacks a concrete declared characterization kind")
        collections = ()
        if partitions is not None:
            owner = next(row for row in model.kinds if row.semantic_id == kind)
            collections = tuple(
                sorted(
                    name
                    for name, spec in json.loads(owner.facts).get("collections", {}).items()
                    if spec["unit"] == "partitioned"
                )
            )
            packet_groups = defaultdict(list)
            for packet in map(json.loads, partitions):
                packet_groups[packet["collection"]].append(packet)
            header = json.loads(content)
            if packet_groups.keys() - set(collections) or any(
                partition_header(packet_groups[name]) != header.get(name) for name in collections
            ):
                raise ValueError(
                    "retained characterization differs from selected partition commitments"
                )
        payload = _characterization_payload(content, prepared, model, definition, collections)
        return cls._from_payload(payload, prepared, model, kind, subject_context, partitions)

    def _require_acquired(self):
        if (
            type(self) is not RetainedCharacterizationProduct
            or "_payload" not in vars(self)
            or self.content is not self._payload.content
        ):
            raise TypeError("retained characterization lacks its acquired payload")

    def __deepcopy__(self, memo):
        self._require_acquired()
        return self

    def with_context(self, context, *, member=None):
        self._require_acquired()
        selection = (self.selected_product, self.selected_member)
        if member is not None:
            from .data_operation_model import BoundRoleMember

            if (
                type(member) is not BoundRoleMember
                or member.member is None
                or member.kind_contract != self._kind_contract
                or context is None
                or context.subject != member.subject
                or context.subject_definition != member.subject_definition
                or context.original_source != member.original_source
                or context.analyzed_scope != member.analyzed_scope
            ):
                raise ValueError("retained characterization requires its exact selected member")
            selection = (member.product, member.member)
        return self._from_payload(
            self._payload, self.prepared, self.model, self.kind, context, self.partitions, selection
        )

    def _publication_context(self):
        if self.subject_context is None:
            raise ValueError(
                "native product identity requires an explicit acquired subject context"
            )
        return self.subject_context

    @property
    def value(self) -> Mapping[str, Any]:
        self._require_acquired()
        return self._payload.value

    @cached_property
    def _kind_contract(self):
        return next(
            row.key
            for row in self.model.identities
            if row.owner == self.kind and row.domain == "kind"
        )

    @cached_property
    def semantic_id(self):
        self._require_acquired()
        if self.selected_product is not None:
            return self.selected_product
        return contextual_product_identity(
            kind=self._kind_contract,
            context=self._publication_context(),
            body=self._payload.body_digest,
        ).key


@dataclass(frozen=True, init=False)
class EnrichedDocumentProduct:
    kind_name: ClassVar[str] = "DdoEnrichedDocumentView"
    content: bytes
    prepared: PreparedRelease
    model: EffectiveDataOperationModel
    subject_context: SubjectContext | None
    _payload: ClassVar[_CharacterizationPayload]

    def __init__(self, *args, **kwargs):
        raise TypeError("enriched document requires validating acquisition")

    @classmethod
    def _from_payload(cls, payload, prepared, model, context):
        result = object.__new__(cls)
        object.__setattr__(result, "content", payload.content)
        object.__setattr__(result, "prepared", prepared)
        object.__setattr__(result, "model", model)
        object.__setattr__(result, "subject_context", context)
        object.__setattr__(result, "_payload", payload)
        return result

    @classmethod
    def acquire(cls, prepared, model, content, *, subject_context=None):
        if type(content) is not bytes:
            raise TypeError("enriched document requires immutable body bytes")
        definition = prepared.index.definitions[cls.kind_name]
        payload = _characterization_payload(content, prepared, model, definition, ())
        return cls._from_payload(payload, prepared, model, subject_context)

    def _require_acquired(self):
        if (
            type(self) is not EnrichedDocumentProduct
            or "_payload" not in vars(self)
            or self.content is not self._payload.content
        ):
            raise TypeError("enriched document lacks its acquired payload")

    def with_context(self, context):
        self._require_acquired()
        return self._from_payload(self._payload, self.prepared, self.model, context)

    def __deepcopy__(self, memo):
        self._require_acquired()
        return self

    def _publication_context(self):
        if self.subject_context is None:
            raise ValueError(
                "native product identity requires an explicit acquired subject context"
            )
        return self.subject_context

    @property
    def value(self) -> Mapping[str, Any]:
        self._require_acquired()
        return self._payload.value

    def publication(self, role, kind_contract):
        from .data_operation_ports import RoleValue

        self._require_acquired()
        return RoleValue(
            role, kind_contract, self.content, self._payload.meaning, self._payload.members
        )

    @cached_property
    def semantic_id(self):
        self._require_acquired()
        kind = next(
            item.key
            for item in self.model.identities
            if item.owner == self.prepared.index.definitions[self.kind_name].iri
            and item.domain == "kind"
        )
        return contextual_product_identity(
            kind=kind, context=self._publication_context(), body=self._payload.body_digest
        ).key

    @property
    def reference(self):
        return DataProductReference(self.semantic_id)


def freeze_characterization_selection(
    *,
    profile: str,
    products: tuple[SelectedSourceSetEntry, ...] = (),
    active: tuple[SelectedSourceSetEntry, ...] = (),
) -> tuple[FrozenSourceSet, ...]:
    """Freeze retained analytical inputs with their exact selected-read support.

    These pins select existing evidence. Native acquisition checks every read,
    producer output and qualified context before a role can consume the product.
    """
    if profile not in {"source_only", "selected_layers"}:
        raise ValueError("unknown retained characterization profile")
    selected = FrozenSourceSet.from_selected("selected-characterization-products", products)
    active_set = FrozenSourceSet.from_selected("active-characterization-products", active)
    if profile == "source_only" and (selected.entries or active_set.entries):
        raise ValueError("source-only view cannot select analytical products")
    if not set(active_set.entries) <= set(selected.entries):
        raise ValueError("active characterization must be an exact subset of selected products")
    return selected, active_set


def _covers(source, examined, requested):
    """Typed source interval coverage; never infer missing ancestry or language facts."""
    value = source.value
    index = source.selector_index()
    found = False
    for piece in value["pieces"]:
        if piece["kind"] != "native_text":
            continue
        match = index.matches(requested, piece["item_ref"])
        if match is None:
            return False
        if match is not True:
            continue
        left, right = (
            max(piece["start"], requested.get("start", 0)),
            min(piece["end"], requested.get("end", len(value["text"]))),
        )
        if left >= right:
            continue
        found = True
        intervals = sorted(
            (max(left, row.get("start", 0)), min(right, row.get("end", len(value["text"]))))
            for row in examined
            if row["projection"] == value["source"]["projection"]
            and index.matches(row, piece["item_ref"]) is True
        )
        cursor = left
        for a, b in intervals:
            if a > cursor:
                break
            cursor = max(cursor, b)
        if cursor < right:
            return False
    return found or requested in examined


def ordered_composition_inputs(sources, products):
    """Present sets by authenticated source coordinate, without asserting reading order.

    Source and manifest roots originate in independent derivations: their scalar
    producer positions cannot establish a document-wide sequence.
    """
    ordered_sources = tuple(
        sorted(sources, key=lambda source: canonical_bytes(source.value["source"]))
    )
    ordered_products = tuple(
        sorted(
            products,
            key=lambda product: (
                canonical_bytes(json.loads(product.content)["source"]),
                product.semantic_id,
            ),
        )
    )
    return ordered_sources, ordered_products


def compose_enriched_document_values(
    sources,
    products,
    *,
    active=(),
    profile="selected_layers",
    required_families=(),
    check_active=lambda: None,
):
    """Pure finite fan-in over parent-validated source and compact product snapshots."""
    if not sources:
        raise ValueError("combined document view requires explicit original source snapshots")
    source_by_key = {canonical_bytes(source.value["source"]): source for source in sources}
    if len(source_by_key) != len(sources):
        raise ValueError("combined document repeats an original source coordinate")
    documents = {source.value["source"]["document"] for source in sources}
    if len(documents) != 1:
        raise ValueError("combined document sources belong to different original documents")
    document = next(iter(documents))
    owned = {}
    for product in products:
        check_active()
        body = (
            product.value
            if isinstance(product, RetainedCharacterizationProduct)
            else json.loads(product.content)
        )
        if canonical_bytes(body["source"]) not in source_by_key:
            raise ValueError("combined view product has no retained original source coordinate")
        pin = DataProductReference(product.semantic_id)
        if pin in owned:
            raise ValueError("combined view repeats an immutable governed product")
        owned[pin] = (product, body)
    active = tuple(active)
    if len(set(active)) != len(active) or not set(active) <= owned.keys():
        raise ValueError("active characterization must be an exact subset of retained products")
    if profile == "source_only" and (owned or active):
        raise ValueError("source-only view cannot assert selected analytical products")
    if profile not in {"source_only", "selected_layers", "full_characterization"}:
        raise ValueError("unknown enriched document profile")
    for _, body in owned.values():
        declared = {DataProductReference(row["product_id"]) for row in body.get("dependencies", ())}
        if not declared <= owned.keys():
            raise ValueError("combined view is missing an exact selected dependency")
    by_family = {}
    for pin in active:
        body = owned[pin][1]
        coordinate = canonical_bytes(body["source"])
        for row in body["coverage"]:
            if "family" in row:
                by_family.setdefault((coordinate, row["family"]), []).append((pin, row))
    if profile == "full_characterization" and not required_families:
        raise ValueError("full characterization requires its captured declared family profile")
    required = (
        [(coordinate, family) for coordinate in source_by_key for family in required_families]
        if profile == "full_characterization"
        else list(by_family)
    )
    coverage = []
    for coordinate, family in required:
        check_active()
        source = source_by_key[coordinate]
        rows = by_family.get((coordinate, family), ())
        successful = [
            (pin, row)
            for pin, row in rows
            if row["availability"] == "available" and row["outcome"] in {"complete", "empty"}
        ]
        examined = [selector for _, row in successful for selector in row.get("examined", ())]
        complete = bool(successful) and all(
            _covers(source, examined, selector) for selector in source.value["selectors"]
        )
        coverage.append(
            dict(
                source=dict(source.value["source"]),
                family=family,
                availability="available" if complete else "unknown",
                outcome=(
                    "empty"
                    if all(row["outcome"] == "empty" for _, row in successful)
                    else "complete"
                )
                if complete
                else "unknown",
                products=[pin.values() for pin, _ in rows],
                **(
                    {}
                    if complete
                    else {
                        "reason": (
                            "required family lacks complete active characterization "
                            "of exact selected scope"
                        )
                    }
                ),
            )
        )
    complete = all(row["outcome"] in {"complete", "empty"} for row in coverage) and all(
        all("family" in row for row in owned[pin][1]["coverage"]) for pin in active
    )
    return dict(
        original_document=document,
        sources=[thaw_native(source.value) for source in sources],
        profile=profile,
        products=[pin.values() for pin in owned],
        active=[pin.values() for pin in active],
        coverage=coverage,
        outcome="complete" if complete else "partial",
    )


def compose_enriched_document(
    prepared,
    model,
    sources: tuple[FrozenNativeSource, ...],
    products,
    *,
    active=(),
    profile="selected_layers",
    subject_context=None,
):
    """Compose exact retained inputs with original local offsets and source identities."""
    sources = tuple(FrozenNativeSource.acquire(prepared, source) for source in sources)
    value = compose_enriched_document_values(
        sources,
        products,
        active=active,
        profile=profile,
        required_families=tuple(
            characterization_profiles(prepared).get("full_characterization", ())
        ),
    )
    return EnrichedDocumentProduct.acquire(
        prepared, model, canonical_bytes(value), subject_context=subject_context
    )


@dataclass(frozen=True)
class EnrichedDocumentReadings:
    """Exact multi-source document/member reader with no reacquisition or inference."""

    view: EnrichedDocumentProduct
    products: tuple
    _sources: tuple[FrozenNativeSource, ...] = field(init=False, repr=False, compare=False)

    def __post_init__(self):
        body = self.view.value
        expected = tuple(row["product_id"] for row in body.get("products", ()))
        if tuple(product.semantic_id for product in self.products) != expected:
            raise ValueError("combined reader inputs differ from frozen selected products")
        sources = tuple(
            FrozenNativeSource.acquire(self.view.prepared, value) for value in body["sources"]
        )
        checked = compose_enriched_document(
            self.view.prepared,
            self.view.model,
            sources,
            self.products,
            active=tuple(DataProductReference(row["product_id"]) for row in body.get("active", ())),
            profile=body["profile"],
            subject_context=self.view.subject_context,
        )
        if checked.content != self.view.content:
            raise ValueError("combined document differs from its exact retained composition")
        object.__setattr__(self, "_sources", sources)

    def sources(self):
        return self._sources

    def source(self, coordinate=None):
        sources = self.sources()
        if coordinate is None:
            if len(sources) != 1:
                raise ValueError(
                    "multi-source document reads require an explicit source coordinate"
                )
            return sources[0]
        selected = next(
            (source for source in sources if source.value["source"] == coordinate), None
        )
        if selected is None:
            raise ValueError("source coordinate is outside the frozen document view")
        return selected

    def member(self, reference: DataProductMemberReference, *, active_only=False):
        if not isinstance(reference, DataProductMemberReference):
            raise TypeError("combined reader requires a governed semantic member address")
        active = {row["product_id"] for row in self.view.value.get("active", ())}
        if active_only and reference.product.product_id not in active:
            raise ValueError("member is outside selected active characterization")
        product = next(
            (value for value in self.products if value.semantic_id == reference.product.product_id),
            None,
        )
        if product is None:
            raise ValueError("member product is outside frozen document selection")
        body = (
            product.value
            if isinstance(product, RetainedCharacterizationProduct)
            else json.loads(product.content)
        )
        packet = next(
            (
                packet
                for packet in body.get("members", ())
                if packet["member_id"] == reference.member_id
            ),
            None,
        )
        if packet is None:
            raise ValueError("member is not an actual retained canonical packet")
        return thaw_native(packet)
