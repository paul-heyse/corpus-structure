"""Opt-in PE-S33 comparator; acquires no database, provider or original bytes.

After the normal native read has acquired all book construction bindings, call::

    compare_whole_book_construction(
        acquired_original.reference,
        expected_sources=tuple(selected_source_product_references),
        acquired=tuple((port, hydrated_role_values, binding_result) for ...),
    )

The expected source population must come from that whole-book selected read,
never an estimated view count. This callable intentionally has no second DB
loader or environment-based runner. Missing current inputs explicitly refuse.
"""

from collections.abc import Iterable
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any
from unittest.mock import patch

from lark import UnexpectedInput

from corpus_structure.semantic.construction_products import PreparedConstructionProfile
from corpus_structure.semantic.constructions import forest
from corpus_structure.semantic.constructions.declarations import GRAMMAR_FAMILIES
from corpus_structure.semantic.constructions.layers import ConstructionLayer
from semantic.prose_regex_oracle import _regex_parser_oracle

if TYPE_CHECKING:
    from corpus_structure.semantic.characterization_ports import PreparedConstructionPort
    from corpus_structure.semantic.data_operation_bindings import BindingResult
    from corpus_structure.semantic.data_operation_ports import HydratedRoleValue
    from corpus_structure.semantic.data_operation_support import OriginalDocumentRef
    from corpus_structure.semantic.data_product_reference import DataProductReference


BOOK_PROJECT = "nce-grinstead-snell-full-book"
BOOK_DOCUMENT = "doc:38d5d93379c3320aa88457511d38fc25"
BOOK_SHA256 = "763eab9894983ddfd6cd7f84685548d1515a9326a2d9fd015474534460551a5e"
_INVENTORIES = ("terms", "choices", "syntax", "positions", "uninterpreted", "sequences")
_UNPARSED = object()


class MissingBookPrerequisites(ValueError):
    """Actual current source/formal/sentence or complete region inputs are absent."""


@dataclass
class _Region:
    text: str
    atoms: tuple
    terminals: tuple
    name: str
    offset: int
    seconds: float
    forest: Any = _UNPARSED
    error: tuple | None = None
    result: Any = None


def _failure(error):
    return type(error).__name__, getattr(error, "pos_in_stream", None)


def _compare_profile_regions(profile, source, formal, options, *, sentences, subject_context=None):
    """Observe exact production selection; reuse its candidate parse and fold."""
    regions, active = [], []
    original_region, original_parser = ConstructionLayer.region, forest.prepared_parser

    def observe_region(builder, view, start, end, atoms=(), **kwargs):
        terminals = kwargs.get("terminals")
        if terminals is None:
            raise MissingBookPrerequisites("retained primary lexical terminals are missing")
        region = _Region(
            view.text[start:end],
            tuple(atoms),
            terminals,
            f"{view.key}:{start}:{end}",
            start,
            kwargs.get("parse_seconds", 2.0),
        )
        regions.append(region)
        active.append(region)
        try:
            region.result = original_region(builder, view, start, end, atoms, **kwargs)
            return region.result
        finally:
            active.pop()

    def observe_parser(text, atoms, grammar=None, *, terminals=None):
        if not active or grammar is not None:
            raise MissingBookPrerequisites(
                "construction parser lacks its default production region"
            )
        target, region = original_parser(text, atoms, grammar, terminals=terminals), active[-1]

        class Parser:
            def parse(self, value):
                try:
                    region.forest = target.parse(value)
                    return region.forest
                except UnexpectedInput as error:
                    region.error = _failure(error)
                    raise

        return Parser()

    with (
        patch.object(ConstructionLayer, "region", observe_region),
        patch.object(forest, "prepared_parser", observe_parser),
    ):
        product = profile.run(
            source, formal, options, sentences=sentences, subject_context=subject_context
        )
    import json

    for row in json.loads(product.content)["coverage"]:
        if row["family"] in GRAMMAR_FAMILIES and (
            row.get("unexamined") or row["outcome"] in {"unknown", "unsupported", "failed"}
        ):
            raise MissingBookPrerequisites("incomplete actual grammar region coverage: " + str(row))
    if not regions:
        raise MissingBookPrerequisites("no actual production construction regions were acquired")
    from corpus_structure.methods.math.grammar import Expired, OffMainThread, deadline

    records = []
    for region in regions:
        expected_error, expected_forest = None, None
        try:
            with deadline(region.seconds):
                try:
                    expected_forest = _regex_parser_oracle(
                        region.text, region.atoms, terminals=region.terminals
                    ).parse(region.text)
                except UnexpectedInput as error:
                    expected_error = _failure(error)
                assert region.error == expected_error, (region.name, region.error, expected_error)
                if expected_error is not None:
                    assert region.result.outcome == "empty", (region.name, region.result)
                    records.append({"region": region.name, "outcome": "empty"})
                    continue
                if (
                    region.forest is _UNPARSED
                    or region.result.root is None
                    or region.result.reducer is None
                ):
                    raise MissingBookPrerequisites(
                        "candidate region was not completely parsed/folded: " + region.name
                    )
                actual_shape, expected_shape = (
                    _forest_shape(region.forest),
                    _forest_shape(expected_forest),
                )
                assert actual_shape == expected_shape, (
                    "ordered/sharing SPPF differs: " + region.name
                )
                reducer = forest.PackedReducer(
                    region.text, region.atoms, region=region.name, offset=region.offset
                )
                expected_root = reducer.transform(expected_forest)
                assert region.result.root == expected_root, "fold differs: " + region.name
                for name in _INVENTORIES:
                    assert getattr(region.result.reducer, name) == getattr(reducer, name), (
                        region.name,
                        name,
                    )
                records.append(
                    {
                        "region": region.name,
                        "outcome": region.result.outcome,
                    }
                )
        except Expired as error:
            raise MissingBookPrerequisites(
                "reference region deadline expired: " + region.name
            ) from error
        except OffMainThread as error:
            raise MissingBookPrerequisites(
                "comparison requires the managed worker main thread"
            ) from error
    return tuple(records)


def compare_whole_book_construction(
    original: OriginalDocumentRef,
    *,
    expected_sources: tuple[DataProductReference, ...],
    acquired: Iterable[
        tuple[PreparedConstructionPort, tuple[HydratedRoleValue, ...], BindingResult]
    ],
):
    """Explicitly opt in with actual acquired port/role/binding tuples; no inference."""
    if (original.project_id, original.document_key, original.content_hash) != (
        BOOK_PROJECT,
        BOOK_DOCUMENT,
        BOOK_SHA256,
    ):
        raise MissingBookPrerequisites("the exact book project/document/SHA pin is required")
    expected = tuple(reference.product_id for reference in expected_sources)
    acquired = tuple(acquired)
    if not expected or len(expected) != len(set(expected)):
        raise MissingBookPrerequisites(
            "missing or ambiguous current whole-book selected source population"
        )
    if not acquired:
        raise MissingBookPrerequisites(
            "missing current acquired construction bindings and source/formal/sentence products"
        )
    seen, records = set(), []
    for port, values, binding in acquired:
        if (
            binding.operation != "text.constructions/source-native"
            or binding.subject_context is None
            or binding.subject_context.project_id != BOOK_PROJECT
            or binding.subject_context.original_source != BOOK_DOCUMENT
        ):
            raise MissingBookPrerequisites(
                "construction binding is outside the exact original book context"
            )
        missing = {"source", "formal", "sentences"} - {value.role for value in values}
        if missing:
            raise MissingBookPrerequisites(
                "missing current typed prerequisite roles: " + ", ".join(sorted(missing))
            )
        source_role = next(role for role in binding.roles if role.role == "source")
        if (
            len(source_role.members) != 1
            or source_role.members[0].member is not None
            or source_role.members[0].multiplicity != 1
        ):
            raise MissingBookPrerequisites(
                "construction requires one exact whole selected source product"
            )
        source_pin = source_role.members[0].product
        if source_pin in seen or source_pin not in expected:
            raise MissingBookPrerequisites(
                "duplicate or unselected book source product: " + source_pin
            )
        port._verify()
        inputs = port._inputs(values, binding)
        if (
            inputs.source.value["source"]["document"] != BOOK_DOCUMENT
            or not inputs.formal
            or inputs.native is None
        ):
            raise MissingBookPrerequisites(
                "actual current book source/formal/sentence products are incomplete"
            )
        seen.add(source_pin)
        compared = _compare_profile_regions(
            PreparedConstructionProfile(port.prepared, port.model),
            inputs.source,
            inputs.formal,
            port.construction_options(),
            sentences=inputs.native,
        )
        records.extend({"source_product": source_pin, **record} for record in compared)
    if seen != set(expected):
        raise MissingBookPrerequisites(
            "missing acquired book source products: " + ", ".join(sorted(set(expected) - seen))
        )
    return {
        "project": BOOK_PROJECT,
        "document": BOOK_DOCUMENT,
        "sha256": BOOK_SHA256,
        "source_products": list(expected),
        "regions": records,
    }


def _forest_shape(root):
    """Ordered SPPF graph, including sharing, without expanding derivations."""
    from lark.parsers.earley_forest import PackedNode, SymbolNode, TokenNode

    identities: dict[int, int] = {}
    records: list[object] = []

    def rule(value):
        return (
            str(value.origin),
            tuple(str(item) for item in value.expansion),
            str(value.alias),
            value.order,
            value.options.keep_all_tokens,
            value.options.expand1,
            value.options.priority,
            value.options.empty_indices,
        )

    def visit(node):
        if node is None:
            return None
        key = id(node)
        if key in identities:
            return identities[key]
        ordinal = identities[key] = len(records)
        records.append(None)
        if isinstance(node, TokenNode):
            token = node.token
            record = (
                "token",
                token.type,
                str(token),
                token.start_pos,
                token.end_pos,
                token.line,
                token.column,
                token.end_line,
                token.end_column,
                node.priority,
            )
        elif isinstance(node, PackedNode):
            record = (
                "packed",
                rule(node.rule),
                node.start,
                node.priority,
                visit(node.left),
                visit(node.right),
            )
        elif isinstance(node, SymbolNode):
            label = (rule(node.s[0]), node.s[1]) if node.is_intermediate else str(node.s)
            record = (
                "symbol",
                node.is_intermediate,
                label,
                node.start,
                node.end,
                node.priority,
                tuple(visit(child) for child in node.children),
            )
        else:
            raise AssertionError("unexpected native forest node " + type(node).__name__)
        records[ordinal] = record
        return ordinal

    visit(root)
    return records
