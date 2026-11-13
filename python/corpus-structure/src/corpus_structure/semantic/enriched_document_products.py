"""A combined document view preserving every original source coordinate and product."""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import ClassVar

from .characterization import characterization_profiles
from .data_operation_identity import body_identity, contextual_product_identity
from .data_operation_model import SubjectContext, EffectiveDataOperationModel
from .data_product_reference import DataProductMemberReference, DataProductReference
from .identity import canonical_bytes
from .source_products import FrozenNativeSource, source_subject
from .types import PreparedRelease


@dataclass(frozen=True)
class RetainedCharacterizationProduct:
    """An actual concrete nominal kind under the declared characterization marker."""

    content: bytes
    prepared: PreparedRelease
    model: EffectiveDataOperationModel
    kind: str
    subject_context: SubjectContext | None = None

    @classmethod
    def acquire(cls, prepared, model, kind, content, *, subject_context=None):
        definition = next((row for row in prepared.definitions if row.iri == kind), None)
        if (
            definition is None
            or definition.abstract
            or "DdoCharacterizedProduct" not in definition.ancestors
        ):
            raise ValueError("view input lacks a concrete declared characterization kind")
        value = prepared.validate_json(definition.name, content)
        from .data_operation_ports import project_product_members

        project_product_members(model, kind, value.model_dump(mode="python", exclude_unset=True))
        return cls(
            canonical_bytes(value.model_dump(mode="json", exclude_unset=True)),
            prepared,
            model,
            kind,
            subject_context,
        )

    def _publication_context(self):
        if self.subject_context is None:
            raise ValueError("native product identity requires an explicit acquired subject context")
        return self.subject_context

    @property
    def value(self):
        definition = next(row for row in self.prepared.definitions if row.iri == self.kind)
        return self.prepared.validate_json(definition.name, self.content)

    @property
    def semantic_id(self):
        kind = next(
            row.key
            for row in self.model.identities
            if row.owner == self.kind and row.domain == "kind"
        )
        value = self.value.model_dump(mode="python", exclude_unset=True)
        return contextual_product_identity(
            kind=kind, context=self._publication_context(), body=body_identity(value).key
        ).key


@dataclass(frozen=True)
class EnrichedDocumentProduct:
    kind_name: ClassVar[str] = "DdoEnrichedDocumentView"
    content: bytes
    prepared: PreparedRelease
    model: EffectiveDataOperationModel
    subject_context: SubjectContext | None = None

    def _publication_context(self):
        if self.subject_context is None:
            raise ValueError("native product identity requires an explicit acquired subject context")
        return self.subject_context

    @property
    def value(self):
        return self.prepared.validate_json(self.kind_name, self.content)

    @property
    def semantic_id(self):
        value = self.value.model_dump(mode="python", exclude_unset=True)
        kind = next(
            item.key
            for item in self.model.identities
            if item.owner == self.prepared.index.definitions[self.kind_name].iri
            and item.domain == "kind"
        )
        return contextual_product_identity(
            kind=kind, context=self._publication_context(), body=body_identity(value).key
        ).key

    @property
    def reference(self):
        return DataProductReference(self.semantic_id)


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
    sources = tuple(FrozenNativeSource.acquire(prepared, source.value) for source in sources)
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
        body = product.value.model_dump(mode="json", exclude_unset=True)
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
    declared_profiles = characterization_profiles(prepared)
    if profile == "full_characterization" and not declared_profiles.get("full_characterization"):
        raise ValueError("full characterization requires its captured declared family profile")
    required = (
        [
            (coordinate, family)
            for coordinate in source_by_key
            for family in declared_profiles["full_characterization"]
        ]
        if profile == "full_characterization"
        else list(by_family)
    )
    coverage = []
    for coordinate, family in required:
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
                source=source.value["source"],
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
    value = dict(
        original_document=document,
        sources=[source.value for source in sources],
        profile=profile,
        products=[pin.values() for pin in owned],
        active=[pin.values() for pin in active],
        coverage=coverage,
        outcome="complete" if complete else "partial",
    )
    checked = prepared.validate_json("DdoEnrichedDocumentView", canonical_bytes(value))
    return EnrichedDocumentProduct(
        canonical_bytes(checked.model_dump(mode="json", exclude_unset=True)), prepared, model, subject_context
    )


@dataclass(frozen=True)
class EnrichedDocumentReadings:
    """Exact multi-source document/member reader with no reacquisition or inference."""

    view: EnrichedDocumentProduct
    products: tuple

    def __post_init__(self):
        body = self.view.value.model_dump(mode="json", exclude_unset=True)
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

    def sources(self):
        return tuple(
            FrozenNativeSource.acquire(self.view.prepared, value)
            for value in json.loads(self.view.content)["sources"]
        )

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
        active = {row["product_id"] for row in json.loads(self.view.content).get("active", ())}
        if active_only and reference.product.product_id not in active:
            raise ValueError("member is outside selected active characterization")
        product = next(
            (value for value in self.products if value.semantic_id == reference.product.product_id),
            None,
        )
        if product is None:
            raise ValueError("member product is outside frozen document selection")
        packet = next(
            (
                packet
                for packet in json.loads(product.content).get("members", ())
                if packet["member_id"] == reference.member_id
            ),
            None,
        )
        if packet is None:
            raise ValueError("member is not an actual retained canonical packet")
        return packet
