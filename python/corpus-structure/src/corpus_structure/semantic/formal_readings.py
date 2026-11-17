"""Exact working projections of retained formal field syntax, without recognition."""

from __future__ import annotations

from bisect import bisect_left, bisect_right
from collections.abc import Mapping
from dataclasses import dataclass
from functools import cached_property
from types import MappingProxyType
from typing import Any

from .data_product_reference import (
    DataProductMemberReference,
    DataProductReference,
    member_reference,
)


@dataclass(frozen=True, slots=True)
class SemanticFormalSource:
    coordinate: bytes
    projection_digest: str


def _reference(pin: DataProductReference, local_id: str):
    return member_reference(pin, local_id)


@dataclass(frozen=True, slots=True)
class FormalFieldReading:
    reference: DataProductMemberReference
    input_reference: DataProductMemberReference
    start: int
    end: int
    text: str
    grammar: str
    rule: str
    normalized: Mapping[str, Any]
    start_symbol: str


@dataclass(frozen=True, slots=True)
class ComparisonBasisReading:
    reference: DataProductMemberReference
    start: int
    end: int
    text: str
    value: str


@dataclass(frozen=True, slots=True)
class LexicalFact:
    reference: DataProductMemberReference
    start: int
    end: int
    text: str
    kind: str
    value: str
    bindings: tuple[tuple[str, DataProductMemberReference, str], ...] = ()


@dataclass(frozen=True)
class _IntervalRows:
    starts: tuple[int, ...]
    maximum_ends: tuple[int, ...]
    rows: tuple[tuple[int, dict, dict], ...]

    @classmethod
    def build(cls, rows):
        ordered = tuple(sorted(rows, key=lambda row: (row[2]["start"], row[0])))
        maximum, ends = -1, []
        for _, _, part in ordered:
            maximum = max(maximum, part["end"])
            ends.append(maximum)
        return cls(tuple(part["start"] for _, _, part in ordered), tuple(ends), ordered)

    def selected(self, start, end, *, overlapping=False):
        if overlapping:
            first = bisect_right(self.maximum_ends, start)
            last = bisect_left(self.starts, end)
            eligible = (row for row in self.rows[first:last] if row[2]["end"] > start)
        else:
            first, last = bisect_left(self.starts, start), bisect_left(self.starts, end)
            eligible = (
                row for row in self.rows[first:last] if row[2]["start"] < row[2]["end"] <= end
            )
        return tuple((node, part) for _, node, part in sorted(eligible, key=lambda row: row[0]))


class _RetainedReadings:
    def __init__(self, pin, body, source):
        self.pin, self.body, self.source = pin, body, source

    @cached_property
    def occurrences(self):
        return {row["local_id"]: row for row in self.body["occurrences"]}

    @cached_property
    def annotations(self):
        return {row["local_id"]: row for row in self.body["annotations"]}

    @cached_property
    def memberships(self):
        result = {}
        for row in self.body["memberships"]:
            result.setdefault(row["group"], []).append(row)
        return {key: tuple(rows) for key, rows in result.items()}

    @cached_property
    def coverage(self):
        result = {}
        for row in self.body["coverage"]:
            result.setdefault(row["family"], row)
        return result

    @cached_property
    def parts(self):
        return {
            key: _extent(node, self.occurrences, self.source)
            for key, node in self.annotations.items()
        }

    @cached_property
    def intervals(self):
        result = {}
        for ordinal, node in enumerate(self.annotations.values()):
            target = (
                node.get("formal", {}).get("input_id")
                if node["kind"] == "formal.rule"
                else node["local_id"]
            )
            part = self.parts.get(target)
            if part is None:
                continue
            result.setdefault((node["kind"], node["family"]), []).append((ordinal, node, part))
            if "formal_input" in node:
                result.setdefault(("formal_input", node["family"]), []).append(
                    (ordinal, node, part)
                )
        return {key: _IntervalRows.build(rows) for key, rows in result.items()}

    @cached_property
    def ordinals(self):
        return {key: index for index, key in enumerate(self.annotations)}

    def selected(self, kind, family, start, end, *, overlapping=False):
        groups = (
            (self.intervals.get((kind, family)),)
            if family is not None
            else tuple(
                value for (candidate, _), value in self.intervals.items() if candidate == kind
            )
        )
        # A kind is currently owned by one family. Keep original annotation order
        # even if a future declared kind is shared by more than one family.
        ordinal = self.ordinals if family is None else None
        rows = [
            row
            for group in groups
            if group is not None
            for row in group.selected(start, end, overlapping=overlapping)
        ]
        return (
            tuple(sorted(rows, key=lambda row: ordinal[row[0]["local_id"]]))
            if ordinal is not None
            else tuple(rows)
        )

    def covered(self, family, start, end):
        return _covered(self.coverage.get(family), self.source, start, end)


class FormalSourceReadings:
    """One operation's exact source index, shared by its field and gap projections."""

    _lexical: tuple[dict[str, Any], ...]
    _text: str
    source: SemanticFormalSource
    _selected: tuple[tuple[DataProductReference, dict[str, Any]], ...]

    @classmethod
    def from_products(cls, products, source):
        """Immediate construction input: retain exact typed facts, never parse again."""
        from .formal_products import FrozenFormalSource, validate_formal_product

        selected = source.value
        coordinate = selected["source"]
        retained = []
        lexical = []
        for product in products:
            # The product's retained examined scope is validated under the same original
            # source, rather than relabelling it as the consumer's requested scope.
            body = product.value.model_dump(mode="json", exclude_unset=True)
            if body["source"] != coordinate:
                raise ValueError("formal construction input belongs to another original source")
            original = FrozenFormalSource.acquire(
                product.prepared, {**selected, "selectors": body["selectors"]}
            )
            checked = validate_formal_product(
                product.prepared,
                body,
                original,
                model=product.model,
                subject_context=product.subject_context,
            )
            retained.append((DataProductReference(checked.semantic_id), checked.inventory()))
            lexical.extend(body["lexicon"])
        return cls._from_retained(selected, retained, lexical)

    @classmethod
    def _from_retained(cls, selected, retained, lexical):
        """Private prepared-kernel read index after its parent authenticated all inputs."""
        from .identity import canonical_bytes

        coordinate = selected["source"]
        instance = cls.__new__(cls)
        instance.source = SemanticFormalSource(
            canonical_bytes(coordinate), coordinate["projection"]
        )
        instance._selected = tuple(retained)
        instance._lexical = tuple(lexical)
        instance._text = selected["text"]
        return instance

    @cached_property
    def _indexes(self):
        return tuple(_RetainedReadings(pin, body, self.source) for pin, body in self._selected)

    def positioned(self, *, start: int, end: int):
        """Exact primary lexical categories and atoms; never recover by classifying again."""
        from .constructions.lexical import PositionedTerminal, ProtectedAtom, region_terminals

        eligible = [
            row
            for row in self._lexical
            if row["start"] <= start <= end <= row["end"] and row["availability"] == "available"
        ]
        if not eligible:
            raise ValueError("primary lexical characterization is unavailable for this region")
        readings = []
        for row in eligible:
            if any(
                a["start"] < end and start < a["end"] and not start <= a["start"] < a["end"] <= end
                for a in row["atoms"]
            ):
                raise ValueError("construction region cuts a protected primary source atom")
            atoms = tuple(
                ProtectedAtom(a["start"] - start, a["end"] - start, a["occurrence"])
                for a in row["atoms"]
                if start <= a["start"] < a["end"] <= end
            )
            terminals = region_terminals(
                tuple(PositionedTerminal(**v) for v in row["terminals"]), self._text, start, end
            )
            readings.append((atoms, terminals))
        if any(value != readings[0] for value in readings[1:]):
            raise ValueError("selected primary lexical characterizations disagree")
        return readings[0]

    def fields(self, *, family: str, start: int, end: int):
        return formal_field_readings(self, self.source, family=family, start=start, end=end)


def _selected(layers: FormalSourceReadings, source):
    if not isinstance(layers, FormalSourceReadings) or layers.source != source:
        raise ValueError("formal reading index belongs to another source")
    yield from layers._indexes


def _extent(row, occurrences, source):
    parts = [part for key in row.get("occurrences", ()) for part in occurrences[key]["extents"]]
    if len(parts) != 1:
        return None
    part = parts[0]
    if (
        part.get("synthetic")
        or "source_view_id" in part
        or part["projection"] != source.projection_digest
        or not isinstance(part.get("text"), str)
    ):
        return None
    return part


def _covered(row, source, start, end):
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
    layers: FormalSourceReadings,
    source,
    *,
    family: str,
    start: int,
    end: int,
) -> tuple[tuple[FormalFieldReading, ...], bool]:
    """Read whole complete input rules; incomplete or rival fields stay unresolved."""
    results, complete, incomplete = [], False, False
    for index in _selected(layers, source):
        pin, annotations = index.pin, index.annotations
        complete |= index.covered(family, start, end)
        captured_roots = set()
        for node, part in index.selected("formal.rule", family, start, end):
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
            if part["text"] != value["text"]:
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
        for root, _part in index.selected("formal_input", family, start, end):
            if root["local_id"] not in captured_roots:
                incomplete = True
    groups = {}
    for value in results:
        groups.setdefault((value.start, value.end), []).append(value)
    if any(len(rows) != 1 for rows in groups.values()):
        incomplete = True
    return tuple(rows[0] for rows in groups.values() if len(rows) == 1), complete and not incomplete


def comparison_basis_readings(
    layers: FormalSourceReadings, source, *, start: int, end: int
) -> tuple[ComparisonBasisReading, ...]:
    results = []
    for index in _selected(layers, source):
        pin = index.pin
        for node, part in index.selected("formal.comparison_basis", None, start, end):
            if (
                node["kind"] != "formal.comparison_basis"
                or node.get("native_scheme") != "source-comparison-basis-1"
            ):
                continue
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
    for index in _selected(layers, source):
        pin, nodes = index.pin, index.annotations
        for node, part in index.selected(kind, "formal.lexical", start, end):
            if node["kind"] != kind or node["family"] != "formal.lexical":
                continue
            value = node.get("native_label")
            if (
                part is None
                or not start <= part["start"] < part["end"] <= end
                or not isinstance(value, str)
                or not value
            ):
                continue
            bindings = []
            for row in index.memberships.get(node["local_id"], ()):
                member = nodes.get(row["member"])
                member_part = index.parts.get(row["member"])
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
    for index in _selected(layers, source):
        if not index.covered("formal.lexical", start, end):
            continue
        pin, nodes = index.pin, index.annotations
        for node, part in index.selected("formal.token", None, start, end, overlapping=True):
            formal = node.get("formal")
            if (
                node["kind"] != "formal.token"
                or formal is None
                or nodes[formal["input_id"]].get("formal_input", {}).get("start_symbol") != "lex"
            ):
                continue
            tokens.append((pin, part["start"], part["end"]))
    return cue if tokens == [(cue.reference.product, cue.start, cue.end)] else None
