"""Exact working projections of retained formal field syntax, without recognition."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from types import MappingProxyType
from typing import Any

from corpus_structure.semantic.characterization import (
    AnnotationReference,
    LayerReport,
    annotation_reference,
)
from corpus_structure.semantic.product_reference import ProductReference


@dataclass(frozen=True, slots=True)
class SemanticFormalPin:
    product: str

    def values(self) -> dict[str, str]:
        return {"product": self.product}


@dataclass(frozen=True, slots=True)
class SemanticFormalReference:
    layer: SemanticFormalPin
    local_id: str

    def values(self) -> dict[str, Any]:
        return {"product": self.layer.product, "local_id": self.local_id}


@dataclass(frozen=True, slots=True)
class SemanticFormalSource:
    coordinate: bytes
    projection_digest: str


def _reference(pin, local_id):
    if isinstance(pin, SemanticFormalPin):
        return SemanticFormalReference(pin, local_id)
    return annotation_reference(pin, local_id)


@dataclass(frozen=True, slots=True)
class FormalFieldReading:
    reference: AnnotationReference | SemanticFormalReference
    input_reference: AnnotationReference | SemanticFormalReference
    start: int
    end: int
    text: str
    grammar: str
    rule: str
    normalized: Mapping[str, Any]
    start_symbol: str


@dataclass(frozen=True, slots=True)
class ComparisonBasisReading:
    reference: AnnotationReference | SemanticFormalReference
    start: int
    end: int
    text: str
    value: str


@dataclass(frozen=True, slots=True)
class LexicalFact:
    reference: AnnotationReference | SemanticFormalReference
    start: int
    end: int
    text: str
    kind: str
    value: str
    bindings: tuple[tuple[str, AnnotationReference | SemanticFormalReference, str], ...] = ()


class FormalSourceReadings:
    """One operation's exact source index, shared by its field and gap projections."""

    def __init__(self, layers, source):
        self.source = source
        self._selected = tuple(_selected(layers, source))

    @classmethod
    def from_products(cls, products, source):
        """Immediate construction input: retain exact typed facts, never parse again."""
        from .formal_products import FrozenFormalSource, validate_formal_product
        from .identity import canonical_bytes

        selected = source.value
        coordinate = selected["source"]
        prepared_source = SemanticFormalSource(
            canonical_bytes(coordinate), coordinate["projection"]
        )
        retained = []
        for product in products:
            # The product's retained examined scope is validated under the same original
            # source, rather than relabelling it as the consumer's requested scope.
            body = product.value.model_dump(mode="json", exclude_unset=True)
            if body["source"] != coordinate:
                raise ValueError("formal construction input belongs to another original source")
            original = FrozenFormalSource.acquire(
                product.prepared, {**selected, "selectors": body["selectors"]}
            )
            checked = validate_formal_product(product.prepared, body, original, model=product.model)
            retained.append((SemanticFormalPin(checked.semantic_id), checked.inventory()))
        instance = cls.__new__(cls)
        instance.source = prepared_source
        instance._selected = tuple(retained)
        return instance

    def fields(self, *, family: str, start: int, end: int):
        return formal_field_readings(self, self.source, family=family, start=start, end=end)


def _selected(layers, source):
    if isinstance(layers, FormalSourceReadings):
        if layers.source != source:
            raise ValueError("formal reading index belongs to another source")
        yield from layers._selected
        return
    for pin, layer in layers.items():
        if layer.reference(pin.task_id) != pin:
            raise ValueError("formal field projection requires exact retained layer pins")
        body = layer.payload
        views = [
            row
            for row in body["source_scope"]["source_views"]
            if row["source_view_id"] == source.source_view_id
        ]
        if not views:
            continue
        base = dict(
            task_id=source.native_task_id,
            product_key=source.native_product_key,
            content_digest=source.native_content_digest,
        )
        if (
            len(views) != 1
            or body["base_document"] != base
            or views[0]["base_document"] != base
            or views[0]["projection_digest"] != source.projection_digest
            or views[0]["recipe_digest"] != source.recipe_digest
        ):
            raise ValueError("formal field projection differs from exact source binding")
        yield pin, body


def _extent(row, occurrences, source):
    parts = [part for key in row.get("occurrences", ()) for part in occurrences[key]["extents"]]
    if len(parts) != 1:
        return None
    part = parts[0]
    if (
        part.get("synthetic")
        or (
            "source_view_id" in part
            if isinstance(source, SemanticFormalSource)
            else part["source_view_id"] != source.source_view_id
        )
        or part["projection"] != source.projection_digest
        or not isinstance(part.get("text"), str)
    ):
        return None
    return part


def _covered(body, source, family, start, end):
    row = next((row for row in body["coverage"] if row["family"] == family), None)
    if (
        row is None
        or row["availability"] != "available"
        or row["outcome"] not in {"complete", "empty"}
        or row.get("unexamined")
    ):
        return False
    # A selected original piece may contain whitespace between complete adjacent
    # fields; source selectors retain this exact examined interval themselves.
    return any(
        selector["projection"] == source.projection_digest
        and selector.get("start", 0) <= start < end <= selector.get("end", 0)
        for selector in row["examined"]
    )


def formal_field_readings(
    layers: Mapping[ProductReference, LayerReport] | FormalSourceReadings,
    source,
    *,
    family: str,
    start: int,
    end: int,
) -> tuple[tuple[FormalFieldReading, ...], bool]:
    """Read whole complete input rules; incomplete or rival fields stay unresolved."""
    results, complete, incomplete = [], False, False
    for pin, body in _selected(layers, source):
        complete |= _covered(body, source, family, start, end)
        occurrences = {row["local_id"]: row for row in body["occurrences"]}
        annotations = {row["local_id"]: row for row in body["annotations"]}
        captured_roots = set()
        for node in annotations.values():
            formal = node.get("formal")
            if (
                node["kind"] != "formal.rule"
                or node["family"] != family
                or formal is None
                or "normalized" not in formal
            ):
                continue
            root = annotations.get(formal["input_id"], {})
            value = root.get("formal_input")
            if (
                value is None
                or value["representation"] != "source_text"
                or value["syntax_outcome"] != "complete"
                or formal["start"] != 0
                or formal["end"] != len(value["text"])
            ):
                continue
            part = _extent(root, occurrences, source)
            if (
                part is None
                or not start <= part["start"] < part["end"] <= end
                or part["text"] != value["text"]
            ):
                continue
            normalized = formal["normalized"]
            if normalized["domain_status"] == "invalid":
                incomplete = True
                continue
            captured_roots.add(root["local_id"])
            results.append(
                FormalFieldReading(
                    _reference(pin, node["local_id"]),
                    _reference(pin, root["local_id"]),
                    part["start"],
                    part["end"],
                    part["text"],
                    value["grammar"],
                    formal["rule"],
                    MappingProxyType(normalized),
                    value["start_symbol"],
                )
            )
        for root in annotations.values():
            if root["family"] != family or "formal_input" not in root:
                continue
            part = _extent(root, occurrences, source)
            if (
                part is not None
                and start <= part["start"] < part["end"] <= end
                and root["local_id"] not in captured_roots
            ):
                incomplete = True
    groups = {}
    for value in results:
        groups.setdefault((value.start, value.end), []).append(value)
    if any(len(rows) != 1 for rows in groups.values()):
        incomplete = True
    return tuple(rows[0] for rows in groups.values() if len(rows) == 1), complete and not incomplete


def comparison_basis_readings(
    layers: Mapping[ProductReference, LayerReport], source, *, start: int, end: int
) -> tuple[ComparisonBasisReading, ...]:
    results = []
    for pin, body in _selected(layers, source):
        occurrences = {row["local_id"]: row for row in body["occurrences"]}
        for node in body["annotations"]:
            if (
                node["kind"] != "formal.comparison_basis"
                or node.get("native_scheme") != "source-comparison-basis-1"
            ):
                continue
            part = _extent(node, occurrences, source)
            value = node.get("native_label")
            if (
                part is not None
                and start <= part["start"] < part["end"] <= end
                and isinstance(value, str)
                and value
            ):
                results.append(
                    ComparisonBasisReading(
                        _reference(pin, node["local_id"]),
                        part["start"],
                        part["end"],
                        part["text"],
                        value,
                    )
                )
    return tuple(results)


def lexical_fact_readings(
    layers, source, *, kind: str, start: int, end: int
) -> tuple[LexicalFact, ...]:
    results = []
    for pin, body in _selected(layers, source):
        occurrences = {row["local_id"]: row for row in body["occurrences"]}
        nodes = {row["local_id"]: row for row in body["annotations"]}
        for node in nodes.values():
            if node["kind"] != kind or node["family"] != "formal.lexical":
                continue
            part = _extent(node, occurrences, source)
            value = node.get("native_label")
            if (
                part is None
                or not start <= part["start"] < part["end"] <= end
                or not isinstance(value, str)
                or not value
            ):
                continue
            bindings = []
            for row in body["memberships"]:
                if row["group"] != node["local_id"]:
                    continue
                member = nodes.get(row["member"])
                member_part = _extent(member, occurrences, source) if member is not None else None
                if (
                    member is None
                    or member_part is None
                    or member.get("native_label") != member_part["text"]
                ):
                    raise ValueError(
                        "formal lexical declaration has no exact named identifier member"
                    )
                bindings.append(
                    (
                        row["role"],
                        _reference(pin, member["local_id"]),
                        member["native_label"],
                    )
                )
            results.append(
                LexicalFact(
                    _reference(pin, node["local_id"]),
                    part["start"],
                    part["end"],
                    part["text"],
                    kind,
                    value,
                    tuple(bindings),
                )
            )
    return tuple(results)


def coordination_reading(layers, source, *, start: int, end: int) -> LexicalFact | None:
    cues = lexical_fact_readings(
        layers, source, kind="formal.coordination_cue", start=start, end=end
    )
    if len(cues) != 1:
        return None
    (cue,) = cues
    tokens = []
    for pin, body in _selected(layers, source):
        if not _covered(body, source, "formal.lexical", start, end):
            continue
        nodes = {row["local_id"]: row for row in body["annotations"]}
        occurrences = {row["local_id"]: row for row in body["occurrences"]}
        for node in nodes.values():
            formal = node.get("formal")
            if (
                node["kind"] != "formal.token"
                or formal is None
                or nodes[formal["input_id"]].get("formal_input", {}).get("start_symbol") != "lex"
            ):
                continue
            part = _extent(node, occurrences, source)
            if part is not None and part["start"] < end and start < part["end"]:
                tokens.append((pin, part["start"], part["end"]))
    return cue if tokens == [(cue.reference.layer, cue.start, cue.end)] else None
