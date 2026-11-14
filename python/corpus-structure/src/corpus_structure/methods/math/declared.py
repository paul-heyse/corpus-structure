"""Mathematical consumers of explicit original-relative sources and retained syntax."""

from __future__ import annotations

from corpus_structure.semantic.declared_record_sources import DeclaredNativeFrameSource
from corpus_structure.semantic.formal_forest import SourceNativeMathReadings
from corpus_structure.semantic.source_products import FrozenNativeSource

from . import grammar
from .native import prepare_native_readings
from .native_topology import prepare_native_topology_columns
from .pdf import formula_occurrence


def selected_formula_inputs(source: FrozenNativeSource):
    """Separate fully selected original formula atoms from clipped/unknown scope.

    Formula coordinates remain local to the recognized atom. A clipped projection
    never permits inspecting the rest of that atom as if it were selected text.
    """
    value = source.value
    index = source.selector_index()
    pieces = {}
    for piece in value["pieces"]:
        if piece.get("item_ref"):
            pieces.setdefault(piece["item_ref"], []).append(piece)
    selected, unexamined = set(), set()
    for item in value["items"]:
        if item["label"] != "formula":
            continue
        pointer = item["self_ref"]
        projected = [
            piece
            for piece in pieces.get(pointer, ())
            if value["text"][piece["start"] : piece["end"]] == item["text"]
        ]
        for selector in value["selectors"]:
            matches = index.matches(selector, pointer)
            if matches is False:
                continue
            if matches is None:
                unexamined.add(pointer)
                continue
            start, end = selector.get("start", 0), selector.get("end", len(value["text"]))
            if projected:
                if any(start <= piece["start"] < piece["end"] <= end for piece in projected):
                    selected.add(pointer)
                elif any(start < piece["end"] and piece["start"] < end for piece in projected):
                    unexamined.add(pointer)
            elif "start" not in selector and "end" not in selector:
                selected.add(pointer)
            else:
                unexamined.add(pointer)
    return frozenset(selected), frozenset(unexamined - selected)


def declared_math_readings(
    source: DeclaredNativeFrameSource,
    formal,
    configuration,
    *,
    prepared,
    prepare_context,
    inherited=(),
    context_issues=(),
    blocks=(),
    check_active=lambda: None,
):
    """Run the original occurrence kernel without a Reader or reparsing.

    The producer supplies its admitted context preparer, selected ancestor declarations and any
    unavailable-context diagnostics. Domain-rule blocks must come from the bound
    primary scope operation; this function does not discover linguistic rules.
    """
    if not isinstance(source, DeclaredNativeFrameSource):
        raise TypeError("declared mathematics requires its actual semantic source member")
    frozen = FrozenNativeSource.acquire(prepared, source.value)
    retained = SourceNativeMathReadings(frozen, tuple(formal))
    section = configuration.section()
    if section.native_domain_rules and not blocks:
        raise ValueError("native domain rules require explicitly bound primary scope blocks")
    selected, clipped = selected_formula_inputs(frozen)
    value = frozen.value
    health = {row["pointer"]: row["outcome"] for row in value["recognition"]}
    issues = tuple(
        dict.fromkeys(
            (
                *context_issues,
                *(
                    "clipped or unavailable formula scope: " + pointer
                    for pointer in sorted(clipped)
                ),
            )
        )
    )
    topology = prepare_native_topology_columns(
        root=source.section_pointer,
        text=source.text,
        items=source.items,
        ancestors=source.ancestors,
        pieces=source.pieces,
    )

    def retain(operand, pointer):
        kind = operand.kind or operand.context.kind
        if kind not in grammar.STARTS:
            raise ValueError("primary mathematical input has an unsupported start symbol")
        syntax = retained.syntax(pointer, operand.latex, macros=operand.context.macros, kind=kind)
        inventory = retained.inventory(pointer, operand.latex, macros=operand.context.macros)
        operand.retain_primary_syntax(syntax, primary_input=inventory["input"])

    readings = prepare_native_readings(
        items=source.items,
        text=source.text,
        pieces={piece["item_ref"]: piece for piece in source.pieces if piece.get("item_ref")},
        health=health,
        section=section,
        seconds=getattr(configuration, "parse_seconds", grammar.PARSE_SECONDS),
        prepared=prepared,
        source=source.source_key,
        topology=topology,
        inherited=inherited,
        context_issues=issues,
        blocks=blocks,
        occurrence=lambda item: formula_occurrence(source, item, health[item["self_ref"]]),
        retain_syntax=retain,
        selected=lambda item: item["self_ref"] in selected,
        check_active=check_active,
        prepare_context=prepare_context,
    )
    return readings
