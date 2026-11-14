"""Source-view mathematical consumers over qualified native occurrences.

The source view is the execution unit; recognized LaTeX offsets remain occurrence-local.
No PDF paragraph, page, section or formula is persisted as an invented rendition.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, replace
from itertools import pairwise
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict

from corpus_structure.core.evidence import MacroDef, Segment
from corpus_structure.core.method import CoverageDraft, ObservationDraft, UnitResult
from corpus_structure.core.vocab import ObservationKind, ObservationOutcome, ParseOutcome
from corpus_structure.semantic.analysis_contracts import prepare_interpretation_context
from corpus_structure.semantic.constructions.math_scope import NativeDomainRule

from . import grammar
from .native_topology import native_topology
from .pdf import FormulaOccurrence
from .source_context import _heads


class NativeDomainPayload(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    rule_id: str
    pattern: str
    statement_kind: str
    scope_role: str
    source_pointer: str
    start: int
    end: int
    status: Literal["inferred"] = "inferred"


class NativeScopePayload(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    source_pointer: str
    recognized_start: int
    recognized_end: int
    symbol: str
    outcome: Literal["resolved", "unresolved"]
    binding_observation: str | None = None
    binding_pointer: str | None = None
    binding_source_view_id: int | None = None
    binding_projection_digest: str | None = None
    binding_quote: str | None = None
    scope_source_view_id: int | None = None
    scope_projection_digest: str | None = None
    extent: str | None = None
    scope_pointer: str | None = None
    scope_start: int | None = None
    scope_end: int | None = None
    reason: str | None = None


def domain_blocks(view: Any, rules: tuple[NativeDomainRule, ...], *, primary_scope=None):
    """Combine retained source-marker candidates with actual native section topology."""
    if not rules:
        return ()
    if primary_scope is None or not primary_scope.complete:
        raise ValueError("native domain scopes require complete primary source-marker coverage")
    topology = native_topology(view)
    by_pointer = {}
    for _start, pointer, rule in primary_scope.markers:
        by_pointer.setdefault(pointer, set()).add(rule)
    if any(len(values) != 1 for values in by_pointer.values()):
        raise ValueError("native domain item has conflicting released source-marker candidates")
    found = [
        (topology.projected[pointer][0], pointer, next(iter(values)))
        for pointer, values in by_pointer.items()
    ]

    found.sort()
    topology = native_topology(view)
    result = []
    for index, (start, pointer, rule) in enumerate(found):
        section = topology.section(pointer)
        end = topology.bounds[section][1]
        for later, next_pointer, _ in found[index + 1 :]:
            if topology.section(next_pointer) == section:
                end = min(end, later)
                break
        # An organizational child starts a distinct section, not an extension of a local
        # proof/example statement in its parent.
        end = min(
            (
                bounds[0]
                for child, bounds in topology.bounds.items()
                if topology.section_parents.get(child) == section and bounds[0] > start
            ),
            default=end,
        )
        result.append((start, end, pointer, rule))
    return tuple(result)


def _declaration_scope(view: Any, rules: tuple[NativeDomainRule, ...], ordinal: int, blocks):
    """Actual section ancestry and attributed statements constrain forward declarations."""
    return declaration_scope(
        source=f"source-view:{view.ref.id}:{view.ref.projection_digest}:native-order",
        items=view.items,
        topology=native_topology(view),
        rules=rules,
        ordinal=ordinal,
        blocks=blocks,
    )


def declaration_scope(*, source, items, topology, rules, ordinal, blocks):
    """Original forward scope calculation over explicit native columns and semantic source."""

    if not rules:
        return source, f"{source}:item:{ordinal}", ordinal + 1
    pointer = items[ordinal]["self_ref"]
    section = topology.section(pointer)
    owner = f"{source}:section:{section}"
    end = topology.ends[section]
    piece = topology.projected.get(pointer)
    for start, stop, marker, rule in blocks:
        if topology.section(marker) != section:
            continue
        marker_ordinal = topology.order[marker]
        if marker_ordinal > ordinal:
            end = min(end, marker_ordinal)
            break
        if piece is not None and start <= piece[0] < stop:
            owner = f"{source}:statement:{marker}:{rule.rule_id}"
            end = min(
                end,
                min(
                    (
                        n
                        for ref, n in topology.order.items()
                        if n > ordinal
                        and ref in topology.projected
                        and topology.projected[ref][0] >= stop
                    ),
                    default=end,
                ),
            )
    return source, owner, end


def _before_descendant(parent: Any, child: Any, pointer: str) -> bool | None:
    """Prove relative order from retained native containment, not collection indices."""
    return before_descendant_columns(
        parent_items=parent.items, parent_ancestors=parent.ancestors,
        child_items=child.items, child_ancestors=child.ancestors,
        ancestor=parent.ref.section_pointer, child_pointer=child.ref.section_pointer,
        pointer=pointer,
    )


def before_descendant_columns(*, parent_items, parent_ancestors, child_items, child_ancestors,
                              ancestor, child_pointer, pointer) -> bool | None:
    """Prove forward containment order from retained native columns alone."""
    nodes = {
        item["self_ref"]: item
        for item in (*parent_items, *parent_ancestors, *child_items, *child_ancestors)
    }
    root = nodes.get(ancestor)
    if root is None:
        return None

    def branch(ref):
        seen = set()
        while ref != ancestor:
            if ref in seen or ref not in nodes:
                return None
            seen.add(ref)
            owner = (nodes[ref].get("parent") or {}).get("$ref")
            if owner == ancestor:
                return ref
            if owner is None:
                return None
            ref = owner
        return None

    source, target = branch(pointer), branch(child_pointer)
    order = [ref["$ref"] for ref in root.get("children", ())]
    if source not in order or target not in order:
        return None
    return order.index(source) < order.index(target)


def recognition_context_issues(view: Any) -> tuple[str, ...]:
    """Unseen recognition members may contain declarations; usable items remain usable."""
    issues = tuple(
        f"native {universe} recognition context {outcome}: {view.ref.key}"
        for universe in ("display", "inline", "cell")
        if (outcome := view.health.get(universe + "_coverage", "unknown")) != "complete"
    )
    integrated = getattr(view, "integrated_context", None)
    if integrated is not None:
        issues += tuple(
            "integrated recognition context "
            + str(row.get("body", row).get("outcome", "unknown"))
            + ": "
            + str(row.get("coverage_id", "unknown"))
            for row in integrated.get("coverage", ())
            if row.get("body", row).get("outcome", "unknown") != "complete"
        )
    return issues


def ancestor_views(reader: Any, view: Any):
    required = {
        item["self_ref"] for item in view.ancestors if item.get("label") in {"section", "chapter"}
    }
    select = getattr(reader, "ancestor_source_views", None)
    refs = (
        select(view.ref.id)
        if select is not None
        else [
            ref
            for ref in reader.source_views()
            if ref.section_pointer in required and ref.native_product == view.ref.native_product
        ]
    )
    parents = tuple(reader.source_view(ref.id) for ref in refs)
    missing = required - {parent.ref.section_pointer for parent in parents}
    return parents, (
        *("ancestor source context unavailable: " + pointer for pointer in sorted(missing)),
        *(issue for parent in parents for issue in recognition_context_issues(parent)),
    )


def _primary_layers(reader, view, *, scope=False):
    families = ("formal.lexical", "construction.math_scope") if scope else ("formal.lexical",)
    return reader.primary_characterization(view.ref.id, families=families)


def _primary_scope(reader, view, binders, rules):
    from corpus_structure.semantic.constructions.math_scope import retained_math_scope

    return retained_math_scope(
        _primary_layers(reader, view, scope=True), view, binders=binders, rules=rules
    )


def _retain_syntax(operand, view, pointer, layers):
    from corpus_structure.semantic.formal_forest import (
        retained_math_inventory,
        retained_math_syntax,
    )

    kind = operand.kind or operand.context.kind
    if kind not in grammar.STARTS:
        raise ValueError("primary mathematical input has an unsupported start symbol")
    result = retained_math_syntax(
        layers, view, pointer, operand.latex, macros=operand.context.macros, kind=kind
    )
    inventory = retained_math_inventory(
        layers, view, pointer, operand.latex, macros=operand.context.macros
    )
    operand.retain_primary_syntax(result, primary_input=inventory["input"])
    return operand


def native_ancestor_declarations(
    reader: Any,
    view: Any,
    rules: tuple[NativeDomainRule, ...],
    seconds: float = grammar.PARSE_SECONDS,
    *,
    macros=None,
    binders=None,
):
    """Prepare attributable forward-only function roles from authorized native ancestor views."""
    from corpus_structure.semantic.identity import canonical_bytes

    from .prepared import PreparedMathInput

    parents, missing = ancestor_views(reader, view)
    issues = list(missing)
    declarations = []
    source = f"source-view:{view.ref.id}:{view.ref.projection_digest}:native-order"
    for parent in parents:
        layers = _primary_layers(reader, parent)
        scope_readings = _primary_scope(reader, parent, binders, rules) if rules else None
        blocks = domain_blocks(parent, rules, primary_scope=scope_readings)
        health = {
            item["pointer"]: item["outcome"] for item in parent.health.get("formula_outcomes", ())
        }
        for ordinal, item in enumerate(parent.items):
            if item.get("label") != "formula":
                continue
            before = _before_descendant(parent, view, item["self_ref"])
            if before is None:
                issues.append("ancestor declaration source order unavailable: " + item["self_ref"])
            if before is not True:
                continue
            parent_source, scope, _ = _declaration_scope(parent, rules, ordinal, blocks)
            if scope != f"{parent_source}:section:{parent.ref.section_pointer}":
                continue
            if health.get(item["self_ref"]) != "succeeded":
                issues.append(
                    "ancestor function declaration recognition unavailable: " + item["self_ref"]
                )
                continue
            context = prepare_interpretation_context(
                getattr(reader, "prepared", None), macros=macros or {}
            )
            operand = PreparedMathInput(context, item["text"], seconds=seconds)
            syntax = _retain_syntax(operand, parent, item["self_ref"], layers).syntax()
            if syntax.tree is None:
                issues.append(
                    "ancestor function declaration syntax unavailable: " + item["self_ref"]
                )
            for name, (start, end) in _heads(syntax):
                declarations.append(
                    dict(
                        symbol=name,
                        role="function",
                        authority="source",
                        source_id=source,
                        scope=f"{source}:section:{view.ref.section_pointer}",
                        start=0,
                        end=len(view.items),
                        evidence=canonical_bytes(
                            dict(
                                rule="function-definition-1",
                                native_product=parent.ref.native_product.values(),
                                source_view_id=parent.ref.id,
                                projection_digest=parent.ref.projection_digest,
                                pointer=item["self_ref"],
                                recognized_start=start,
                                recognized_end=end,
                                before_descendant=True,
                            )
                        ).decode(),
                    )
                )
    return tuple(declarations), tuple(issues)


class NativeSymbolPayload(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    label: Literal["symbol"] = "symbol"
    text: str
    math: dict[str, Any]
    source_pointer: str
    recognized_start: int
    recognized_end: int
    context_basis: tuple[dict[str, Any], ...] = ()
    context_issues: tuple[str, ...] = ()


class NativeRelationPayload(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    label: str
    source_pointer: str
    recognized_head: tuple[int, int]
    recognized_tail: tuple[int, int]


@dataclass(frozen=True)
class NativeReading:
    pointer: str
    prepared: Any
    result: grammar.MathResult
    projected_start: int | None
    context_issues: tuple[str, ...] = ()


def readings(
    view: Any, cfg: Any, reader: Any, *, demand: str = "occurrences"
) -> tuple[NativeReading, ...]:
    """Prepare one ordered native input universe once per compatible operation batch."""
    from .methods import MathReadingsBatch

    batch = getattr(reader, "math_readings_batch", None)
    if batch is None:
        batch = MathReadingsBatch()
        reader.math_readings_batch = batch
    batch.bind(reader)
    section = cfg.section()
    seconds = getattr(cfg, "parse_seconds", grammar.PARSE_SECONDS)
    layers = _primary_layers(reader, view)
    key = (
        view.ref.id,
        view.ref.projection_digest,
        seconds,
        section.model_dump_json(),
        tuple(layers),
    )
    if key in batch.native:
        base = batch.native[key]
        return (
            base
            if demand == "occurrences"
            else tuple(replace(row, result=row.prepared.symbolic_reading()) for row in base)
        )
    health = {row["pointer"]: row["outcome"] for row in view.health.get("formula_outcomes", ())}
    pieces = {piece["item_ref"]: piece for piece in view.pieces if piece.get("item_ref")}
    inherited, context_issues = native_ancestor_declarations(
        reader, view, section.native_domain_rules, seconds, macros=section.macro_table()
    )
    context_issues = tuple(dict.fromkeys((*recognition_context_issues(view), *context_issues)))
    blocks = domain_blocks(
        view,
        section.native_domain_rules,
        primary_scope=_primary_scope(reader, view, None, section.native_domain_rules)
        if section.native_domain_rules
        else None,
    )
    out = list(
        prepare_native_readings(
            items=view.items,
            text=view.text,
            pieces=pieces,
            health=health,
            section=section,
            seconds=seconds,
            prepared=getattr(reader, "prepared", None),
            source=f"source-view:{view.ref.id}:{view.ref.projection_digest}:native-order",
            topology=native_topology(view),
            inherited=inherited,
            context_issues=context_issues,
            blocks=blocks,
            occurrence=lambda item: FormulaOccurrence(
                view.ref.native_product.content_digest,
                item["self_ref"],
                item["text"],
                item.get("orig", ""),
                "succeeded",
            ),
            retain_syntax=lambda operand, pointer: _retain_syntax(operand, view, pointer, layers),
        )
    )
    batch.native[key] = tuple(out)
    return (
        tuple(out)
        if demand == "occurrences"
        else tuple(replace(row, result=row.prepared.symbolic_reading()) for row in out)
    )


def prepare_native_readings(
    *,
    items,
    text,
    pieces,
    health,
    section,
    seconds,
    prepared,
    source,
    topology,
    inherited,
    context_issues,
    blocks,
    occurrence,
    retain_syntax,
    selected=lambda item: True,
    check_active=lambda: None,
    prepare_context=prepare_interpretation_context,
):
    """Original occurrence algorithm on explicit source columns and retained primary syntax.

    Callers select their admitted source population and provide actual declaration context;
    this kernel has no reader, task lookup, recognition or ambient source discovery.
    """
    definitions = list(inherited)
    out = []
    for ordinal, item in enumerate(items):
        if item.get("label") != "formula":
            continue
        pointer = item["self_ref"]
        check_active()
        if not selected(item):
            continue
        if health.get(pointer) != "succeeded":
            continue
        latex = item["text"]
        piece = pieces.get(pointer)
        start = None
        if piece is not None and text[piece["start"] : piece["end"]] == latex:
            start = piece["start"]
        source_id, scope, end = declaration_scope(
            source=source,
            items=items,
            topology=topology,
            rules=section.native_domain_rules,
            ordinal=ordinal,
            blocks=blocks,
        )
        context = prepare_context(
            prepared,
            macros=section.macro_table(),
            constants=section.constants,
            source_id=source_id,
            scope=scope,
            offset=ordinal,
            scope_chain=topology.scope_chain(pointer, source_id),
            declarations=definitions,
            demand="occurrences",
        )
        operand = occurrence(item).prepare(context).operand
        operand = replace(operand, seconds=seconds)
        retain_syntax(operand, pointer)
        recognized = operand.syntax()
        # The admitted native rule supplies the mathematical head; visual adjacency never
        # turns an arbitrary identifier into a function declaration.
        if context.allow_local_definitions:
            for symbol, extent in _heads(recognized):
                definitions.append(
                    dict(
                        symbol=symbol,
                        role="function",
                        authority="source",
                        evidence=f"{pointer}:{extent[0]}:{extent[1]}",
                        source_id=context.source_id,
                        scope=scope,
                        start=ordinal + 1,
                        end=end,
                    )
                )
        result = operand.interpretation()
        out.append(NativeReading(pointer, operand, result, start, context_issues))
    return tuple(out)


def required_occurrence_record(reader: Any, view: Any):
    records = [
        row
        for row in reader.source_observations(view.ref.id, "extract.math", ObservationKind.RECORD)
        if row.payload.get("demand") == "occurrences"
        and row.payload.get("source_view_id") == view.ref.id
        and row.payload.get("native_product") == view.ref.native_product.values()
        and row.payload.get("projection_digest") == view.ref.projection_digest
        and row.payload.get("recipe_digest") == view.ref.recipe_digest
    ]
    if len(records) != 1:
        raise ValueError("normalization requires one exact completed same-view occurrence RECORD")
    return records[0]


def _restore_reading(record: dict[str, Any], latex: str, context: Any) -> grammar.MathResult:
    from lark import Token, Tree
    from lark.tree import Meta

    syntax = record.get("syntax")
    tree = None
    if syntax is not None:
        if syntax.get("format") != "lark-working-dag-1":
            raise ValueError("retained native syntax requires the current working DAG codec")
        rows = syntax.get("nodes")
        if not isinstance(rows, list) or not rows or len(rows) > 20000:
            raise ValueError("retained native syntax has an invalid node inventory")
        restored, active = {}, set()

        def restore(key):
            if type(key) is not int or key < 0 or key >= len(rows):
                raise ValueError("retained native syntax has an invalid child reference")
            if key in restored:
                return restored[key]
            if key in active:
                raise ValueError("retained native syntax contains a cycle")
            active.add(key)
            row = rows[key]
            if "token" in row:
                value = Token(row["token"], row["text"], start_pos=row["start"], end_pos=row["end"])
            else:
                meta = Meta()
                if row.get("extent") is not None:
                    meta.empty = False
                    meta.start_pos, meta.end_pos = row["extent"]
                value = Tree(row["rule"], [restore(child) for child in row["children"]], meta=meta)
            active.remove(key)
            restored[key] = value
            return value

        tree = restore(syntax["root"])
    if tree is not None and not isinstance(tree, Tree):
        raise ValueError("retained native syntax root must be a tree")
    return grammar.MathResult(
        latex,
        "any_value",
        ParseOutcome(record["outcome"]),
        kind=record.get("kind"),
        tree=tree,
        failure=None if record.get("failure") is None else grammar.Failure(**record["failure"]),
        notes=tuple(record.get("notes", ())),
        tail=record.get("tail", ""),
        occurrences=tuple(grammar.Occurrence(**o) for o in record.get("occurrences", ())),
        context=context.grammar_context,
        macros=context.macros,
        classes=grammar.classify(context.macros),
        declarations=tuple(grammar.LocalDeclaration(**d) for d in record.get("declarations", ())),
    )


def normalization_readings(view: Any, cfg: Any, reader: Any) -> tuple[NativeReading, ...]:
    """Normalize the exact retained occurrence product; do not recognize formulas again."""
    from .prepared import PreparedMathInput

    source = required_occurrence_record(reader, view)
    items = {item["self_ref"]: n for n, item in enumerate(view.items)}
    pieces = {piece["item_ref"]: piece for piece in view.pieces if piece.get("item_ref")}
    result = []
    for record in source.payload["items"]:
        pointer = record["pointer"]
        basis = record["context"]
        source_id = basis["source_id"]
        declarations = [d for d in basis["declarations"] if d["authority"] == "source"]
        context = prepare_interpretation_context(
            getattr(reader, "prepared", None),
            macros=cfg.section().macro_table(),
            constants=cfg.section().constants,
            source_id=source_id,
            scope=basis["scope"],
            offset=items[pointer],
            scope_chain=native_topology(view).scope_chain(pointer, source_id),
            declarations=declarations,
            demand="occurrences",
        )
        if context.stage_key("occurrences") != record["occurrence_basis"]:
            raise ValueError("normalization occurrence context differs from its named input")
        operand = PreparedMathInput(context, record["recognized_latex"], seconds=cfg.parse_seconds)
        syntax = _restore_reading(record.get("raw_syntax", record), operand.latex, context)
        weak = _restore_reading(record, operand.latex, context)
        operand.retain_primary_syntax(syntax, primary_input=record.get("primary_input"))
        object.__setattr__(operand, "_reading", weak)
        operand._remember("syntax", syntax)
        operand._remember("interpretation", weak)
        operand._states["occurrences"] = operand.state("interpretation")
        piece = pieces.get(pointer)
        position = None
        if piece is not None and view.text[piece["start"] : piece["end"]] == operand.latex:
            position = piece["start"]
        result.append(
            NativeReading(
                pointer,
                operand,
                operand.symbolic_reading(),
                position,
                tuple(basis.get("issues", ())),
            )
        )
    return tuple(result)


def native_reading_record(reading: NativeReading, *, original: str, demand: str) -> dict[str, Any]:
    """Retain the existing mathematical result without a task/view envelope.

    Both native publication routes use this codec; interpretation and symbolic
    evaluation remain with the prepared mathematical operand.
    """
    import dataclasses

    import sympy

    from .transform import NotRepresentable

    operand = reading.prepared
    record = dict(
        pointer=reading.pointer,
        orig=original,
        recognized_latex=operand.latex,
        primary_input=operand._primary_input,
        recognition_health="succeeded",
        context_basis=operand.context.stage_key(demand),
        occurrence_basis=operand.context.stage_key("occurrences"),
        context=dict(
            source_id=operand.context.source_id,
            scope=operand.context.scope,
            declarations=[dataclasses.asdict(d) for d in operand.context.declarations],
            issues=reading.context_issues,
        ),
        **_syntax_value(reading.result),
    )
    if demand == "occurrences":
        syntax_record = _syntax_value(operand.syntax())
        if syntax_record != _syntax_value(operand.interpretation()):
            record["raw_syntax"] = syntax_record
    if demand == "symbolic":
        record["weak_interpretation"] = _syntax_value(operand.interpretation())
        try:
            record["symbolic"] = dict(
                format="sympy-srepr-1", expression=sympy.srepr(operand.symbolic_value())
            )
        except (NotRepresentable, grammar.NotParsed, grammar.Ambiguous) as error:
            record["symbolic"] = dict(outcome="unsupported", diagnostic=str(error))
        record["definedness"] = dataclasses.asdict(operand.definedness_result())
    record["stages"] = {
        name: dataclasses.asdict(operand.state(name))
        for name in (
            "lexical",
            "syntax",
            "interpretation",
            "occurrences",
            "symbolic",
            "scientific",
        )
    }
    return record


def native_result(unit: Any, cfg: Any, ctx: Any, method: str) -> UnitResult:
    from corpus_structure.core.evidence import Segment
    from corpus_structure.core.payloads import ValuePayload
    from corpus_structure.core.vocab import SegmentKind

    from .spans import MathSpan, SpanReading, formula_values

    view = ctx.reader.source_view(unit.ref.unit_id)
    demand = "symbolic" if method == "normalize.formula" else "occurrences"
    if demand == "symbolic":
        selected = normalization_readings(view, cfg, ctx.reader)
    else:
        selected = readings(view, cfg, ctx.reader, demand=demand)
    drafts: list[ObservationDraft[Any]] = []
    for reading in selected:
        text = reading.prepared.latex
        projected = (
            None
            if reading.projected_start is None
            else (reading.projected_start, reading.projected_start + len(text))
        )
        if method == "normalize.formula":
            segment = Segment(kind=SegmentKind.MATH_DISPLAY, start=0, end=len(text))
            value = formula_values(
                [SpanReading(MathSpan(segment, text, 0), reading.result, reading.prepared)]
            )[0]
            fields: dict[str, Any] = {"value": value.value}
            if value.parse_error is not None:
                fields["parse_error"] = value.parse_error
            if value.math_kind is not None:
                fields["math_kind"] = value.math_kind
            payload = ValuePayload(**fields)
            drafts.append(
                ObservationDraft(
                    kind=ObservationKind.VALUE,
                    payload=payload,
                    payload_class=ValuePayload,
                    payload_version="3",
                    source_view_id=view.ref.id,
                    native_pointer=reading.pointer,
                    projected_span=projected,
                    recognized_span=(0, len(text)),
                )
            )
        else:
            for symbol in reading.result.occurrences:
                payload = NativeSymbolPayload(
                    text=text[symbol.start : symbol.end],
                    math=dict(
                        name=symbol.name,
                        base=symbol.base,
                        sub=symbol.sub,
                        sup=symbol.sup,
                        constant=symbol.constant,
                        in_subscript_of=symbol.in_subscript_of,
                    ),
                    source_pointer=reading.pointer,
                    recognized_start=symbol.start,
                    recognized_end=symbol.end,
                    context_basis=tuple(
                        vars(d)
                        for d in reading.prepared.context.declarations
                        if d.authority == "source"
                    ),
                    context_issues=reading.context_issues,
                )
                location = (
                    None
                    if reading.projected_start is None
                    else (
                        reading.projected_start + symbol.start,
                        reading.projected_start + symbol.end,
                    )
                )
                drafts.append(
                    ObservationDraft(
                        kind=ObservationKind.MENTION,
                        payload=payload,
                        payload_class=NativeSymbolPayload,
                        payload_version="3",
                        source_view_id=view.ref.id,
                        native_pointer=reading.pointer,
                        projected_span=location,
                        recognized_span=(symbol.start, symbol.end),
                    )
                )
            if reading.result.tree is not None:
                from .spans import _relations

                for relation in _relations(
                    reading.result.tree,
                    MathSpan(
                        Segment(kind=SegmentKind.MATH_DISPLAY, start=0, end=len(text)), text, 0
                    ),
                ):
                    payload = NativeRelationPayload(
                        label=relation.label,
                        source_pointer=reading.pointer,
                        recognized_head=relation.head,
                        recognized_tail=relation.tail,
                    )
                    drafts.append(
                        ObservationDraft(
                            kind=ObservationKind.RELATION,
                            payload=payload,
                            payload_class=NativeRelationPayload,
                            payload_version="3",
                            source_view_id=view.ref.id,
                            native_pointer=reading.pointer,
                            projected_span=projected,
                            recognized_span=(0, len(text)),
                        )
                    )
    source_items = {item["self_ref"]: item for item in view.items}
    analysis_items = [
        native_reading_record(
            reading, original=source_items[reading.pointer].get("orig", ""), demand=demand
        )
        for reading in selected
    ]
    if analysis_items or demand == "occurrences":
        refs = ()
        if demand == "symbolic":
            from corpus_structure.core.method import SourceObservationReference

            source = required_occurrence_record(ctx.reader, view)
            refs = (SourceObservationReference(source.observation_key, "native_analysis"),)
            for item in analysis_items:
                item.pop("weak_interpretation", None)
                item["interpretation_ref"] = dict(
                    observation_key=source.observation_key, pointer=item["pointer"]
                )
                weak = next(i for i in source.payload["items"] if i["pointer"] == item["pointer"])
                if item.get("syntax") == weak.get("syntax"):
                    item.pop("syntax", None)
                    item.pop("occurrences", None)
        analysis = NativeAnalysisPayload(
            source_view_id=view.ref.id,
            native_product=view.ref.native_product.values(),
            projection_digest=view.ref.projection_digest,
            recipe_digest=view.ref.recipe_digest,
            demand=demand,
            items=tuple(analysis_items),
        )
        drafts.append(
            ObservationDraft(
                kind=ObservationKind.RECORD,
                payload=analysis,
                payload_class=NativeAnalysisPayload,
                payload_version="1",
                source_view_id=view.ref.id,
                input_refs=refs,
            )
        )
    recognized = {r.pointer for r in selected}
    formulas = {i["self_ref"] for i in view.items if i.get("label") == "formula"}
    complete = formulas <= recognized and all(
        r.result.status == ParseOutcome.OK and not r.context_issues for r in selected
    )
    coverage = tuple(
        CoverageDraft(
            family=method,
            scope=view.ref.key,
            outcome="complete"
            if complete
            and view.health.get("inline_coverage") == "complete"
            and view.health.get("cell_coverage") == "complete"
            else "partial",
            reason=None
            if complete
            and view.health.get("inline_coverage") == "complete"
            and view.health.get("cell_coverage") == "complete"
            else "native recognition/interpretation coverage is incomplete",
            required_capability="interpretation",
        )
        for _ in (0,)
    )
    return UnitResult(
        ref=unit.ref,
        outcome=ObservationOutcome.PRODUCED if drafts else ObservationOutcome.EMPTY,
        observations=tuple(drafts),
        coverage=coverage,
    )


def _tree_value(node):
    from lark import Token, Tree

    identities, nodes = {}, []

    def visit(value):
        if id(value) in identities:
            return identities[id(value)]
        key = len(nodes)
        identities[id(value)] = key
        nodes.append(None)
        if isinstance(value, Token):
            row = dict(token=value.type, text=str(value), start=value.start_pos, end=value.end_pos)
        elif isinstance(value, Tree):
            children = [visit(child) for child in value.children]
            extents = [
                (nodes[child]["start"], nodes[child]["end"])
                if "token" in nodes[child]
                else nodes[child]["extent"]
                for child in children
            ]
            positioned = [
                extent
                for extent in extents
                if extent is not None and extent[0] is not None and extent[1] is not None
            ]
            extent = (
                (min(e[0] for e in positioned), max(e[1] for e in positioned))
                if positioned
                else None
            )
            if value.data != "_ambig" and not value.meta.empty:
                extent = value.meta.start_pos, value.meta.end_pos
            row = dict(rule=value.data, extent=extent, children=children)
        else:
            raise TypeError("unsupported positioned syntax node")
        nodes[key] = row
        return key

    root = visit(node)
    return dict(format="lark-working-dag-1", root=root, nodes=nodes)


def _syntax_value(result):
    import dataclasses

    return dict(
        outcome=result.status.value,
        kind=result.kind,
        tail=result.tail,
        failure=None if result.failure is None else dataclasses.asdict(result.failure),
        syntax=None if result.tree is None else _tree_value(result.tree),
        occurrences=[dataclasses.asdict(o) for o in result.occurrences],
        declarations=[dataclasses.asdict(d) for d in result.declarations],
        notes=list(result.notes),
    )


class NativeAnalysisPayload(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    source_view_id: int
    native_product: dict[str, Any]
    projection_digest: str
    recipe_digest: str
    demand: str
    items: tuple[dict[str, Any], ...]


def native_request_analysis(
    view: Any,
    prepared: Any,
    demand: str,
    pointer: str | None = None,
    question: str | None = None,
    predicate: str | None = None,
    seconds: float = grammar.PARSE_SECONDS,
    domain_rules: tuple[NativeDomainRule, ...] = (),
    ancestor_declarations: tuple[dict[str, Any], ...] = (),
    ancestor_context_issues: tuple[str, ...] = (),
    *,
    primary_layers=None,
    macros=None,
    binders=None,
) -> NativeAnalysisPayload:
    """Finite native demand kernel; no converter, database or stronger extraction entrypoint."""
    import dataclasses

    import sympy

    from .prepared import PreparedMathInput
    from .transform import NotRepresentable

    allowed = {
        "lexical",
        "structure",
        "syntax",
        "interpretation",
        "occurrences",
        "symbolic",
        "scientific",
    }
    if demand not in allowed:
        raise ValueError("unsupported native mathematical demand")
    if seconds <= 0:
        raise ValueError("native mathematical deadline must be positive")
    if demand == "scientific" and question is None:
        raise ValueError("scientific demand requires an explicit question")
    formulas = [item for item in view.items if item.get("label") == "formula"]
    if pointer is not None and pointer not in {item["self_ref"] for item in formulas}:
        raise ValueError("formula selector is outside the pinned source view")
    health = {o["pointer"]: o["outcome"] for o in view.health.get("formula_outcomes", ())}
    context_issues = tuple(
        dict.fromkeys((*recognition_context_issues(view), *ancestor_context_issues))
    )

    definitions = list(ancestor_declarations)
    results = []
    positions = {item["self_ref"]: n for n, item in enumerate(view.items)}
    from corpus_structure.semantic.constructions.math_scope import retained_math_scope

    layers = {} if primary_layers is None else primary_layers
    scope_readings = retained_math_scope(layers, view, binders=binders, rules=domain_rules)
    blocks = domain_blocks(view, domain_rules, primary_scope=scope_readings)
    for item in formulas:
        ref = item["self_ref"]
        outcome = health.get(ref, "unknown")
        selected = pointer is None or ref == pointer
        if outcome != "succeeded":
            if selected:
                results.append(
                    dict(
                        pointer=ref,
                        orig=item.get("orig", ""),
                        recognized_latex=item["text"],
                        recognition_health=outcome,
                        availability="unavailable",
                    )
                )
            continue
        ordinal = positions[ref]
        source_id, scope, end = _declaration_scope(view, domain_rules, ordinal, blocks)
        context = prepare_interpretation_context(
            prepared,
            macros=macros or {},
            source_id=source_id,
            scope=scope,
            offset=ordinal,
            scope_chain=native_topology(view).scope_chain(ref, source_id),
            declarations=definitions,
            demand=demand,
        )
        operand = PreparedMathInput(context, item["text"], seconds=seconds)
        _retain_syntax(operand, view, ref, layers)
        from corpus_structure.semantic.analysis_contracts import scientific_question_rule

        question_rule = (
            scientific_question_rule(context.profile, question)
            if demand == "scientific" and question is not None
            else None
        )
        # Only declared contextual demands need prior mathematical declaration recognition.
        contextual = demand in {"interpretation", "occurrences", "symbolic"} or (
            demand == "scientific" and question_rule is not None
        )
        if contextual and context.allow_local_definitions:
            for symbol, extent in _heads(operand.syntax()):
                definitions.append(
                    dict(
                        symbol=symbol,
                        role="function",
                        authority="source",
                        evidence=f"{ref}:{extent[0]}:{extent[1]}",
                        source_id=context.source_id,
                        scope=scope,
                        start=ordinal + 1,
                        end=end,
                    )
                )
        if not selected:
            continue
        value = dict(
            pointer=ref,
            orig=item.get("orig", ""),
            recognized_latex=item["text"],
            primary_input=operand._primary_input,
            recognition_health=outcome,
            availability="available",
            context_basis=context.stage_key(
                demand,
                **(
                    {
                        "conditions": (
                            []
                            if question_rule is None
                            else [dataclasses.asdict(c) for c in operand.definedness()]
                        ),
                        "precision": {"mode": "exact-symbolic"},
                        "sampling": {"requested": False},
                        "decision_policy": {
                            "question": question,
                            "predicate": predicate,
                            "rule": None
                            if question_rule is None
                            else dataclasses.asdict(question_rule),
                        },
                    }
                    if demand == "scientific"
                    else {}
                ),
            ),
        )
        value["context"] = dict(
            source_id=context.source_id,
            scope=context.scope,
            declarations=[dataclasses.asdict(d) for d in context.declarations],
            coverage="complete" if domain_rules and not context_issues else "unknown",
            issues=context_issues,
        )
        if demand in {"lexical", "structure"}:
            from corpus_structure.semantic.formal_forest import retained_math_inventory

            inventory = retained_math_inventory(
                layers, view, ref, item["text"], macros=context.macros
            )
            if demand == "lexical":
                value["lexical"] = inventory["lexical"]
            else:
                value["structure"] = {
                    key: item for key, item in inventory.items() if key != "lexical"
                }
        elif demand == "syntax":
            value.update(_syntax_value(operand.syntax()))
        else:
            if demand != "scientific" or question_rule is not None:
                value.update(_syntax_value(operand.interpretation()))
            if demand == "symbolic":
                try:
                    native = operand.symbolic_value()
                    value["symbolic"] = dict(format="sympy-srepr-1", expression=sympy.srepr(native))
                except (NotRepresentable, grammar.NotParsed, grammar.Ambiguous) as error:
                    value["symbolic"] = dict(outcome="unsupported", diagnostic=str(error))
                value["definedness"] = dataclasses.asdict(operand.definedness_result())
            if demand == "scientific":
                assert question is not None
                assessment = operand.assess(question, predicate=predicate)
                value["scientific_question"] = (
                    None if question_rule is None else dataclasses.asdict(question_rule)
                )
                if question_rule is not None:
                    value["definedness"] = dataclasses.asdict(operand.definedness_result())
                    if "symbolic" in question_rule.result_basis:
                        try:
                            value["symbolic"] = dict(
                                format="sympy-srepr-1",
                                expression=sympy.srepr(operand.symbolic_value()),
                            )
                        except (NotRepresentable, grammar.NotParsed, grammar.Ambiguous) as error:
                            value["symbolic"] = dict(outcome="unsupported", diagnostic=str(error))
                value["assessment"] = dict(
                    question=assessment.question,
                    outcome=assessment.outcome,
                    value=None
                    if assessment.value is None or question == "definedness"
                    else sympy.srepr(assessment.value),
                    conditions=[dataclasses.asdict(c) for c in assessment.conditions],
                    diagnostic=assessment.diagnostic,
                    coverage=assessment.coverage,
                )
        value["stages"] = {name: dataclasses.asdict(operand.state(name)) for name in allowed}
        results.append(value)
    return NativeAnalysisPayload(
        source_view_id=view.ref.id,
        native_product=view.ref.native_product.values(),
        projection_digest=view.ref.projection_digest,
        recipe_digest=view.ref.recipe_digest,
        demand=demand,
        items=tuple(results),
    )


def native_proposal_packet(
    reader: Any,
    source_view_id: int,
    prepared: Any,
    configuration: Any,
    *,
    known: tuple[Any, ...] = (),
):
    """Build one intact section packet from pinned native context and stored upstream facts."""
    from corpus_structure.semantic.proposals import (
        KnownProposalEntity,
        native_frame_source,
        native_source_frame,
        proposal_packet,
    )

    view = reader.source_view(source_view_id)
    raw = (
        configuration.model_dump(mode="python")
        if isinstance(configuration, BaseModel)
        else configuration
    )
    from corpus_structure.semantic.constructions.math_scope import Binders

    binders = Binders.model_validate(raw["binders"]) if raw.get("binders") is not None else None
    rules = tuple(
        NativeDomainRule.model_validate(rule)
        for rule in (raw.get("math") or {}).get("native_domain_rules", ())
    )
    primary_scope = _primary_scope(reader, view, binders, rules)
    if not primary_scope.complete:
        raise ValueError("native packet requires complete primary sentence evidence")
    extents = primary_scope.sentences
    frame = native_source_frame(
        view, [(f"s{index + 1}", start, end) for index, (start, end) in enumerate(extents)]
    )
    parent_views, _ = ancestor_views(reader, view)
    contexts = []
    for parent in parent_views:
        if parent.ref.membership != "direct":
            raise ValueError("native standing context requires a direct ancestor source view")
        parent_scope = _primary_scope(reader, parent, binders, rules)
        if not parent_scope.complete:
            raise ValueError("native context packet requires complete primary sentence evidence")
        parent_extents = parent_scope.sentences
        parent_frame = native_source_frame(
            parent,
            [(f"s{index + 1}", start, end) for index, (start, end) in enumerate(parent_extents)],
        )
        contexts.append(native_frame_source(parent_frame))
    frame = replace(frame, context_sources=tuple(contexts))
    observations = []
    for kind in (ObservationKind.SCOPE, ObservationKind.AUTHOR_MARKUP):
        for row in reader.source_observations(source_view_id, "resolve.symbol_scope", kind):
            observations.append(
                dict(observation_key=row.observation_key, kind=str(kind), payload=dict(row.payload))
            )
    observations.extend(
        dict(
            kind="coverage",
            family="resolve.symbol_scope",
            task_id=row.task_id,
            release_id=row.release_id,
            coverage=__import__("dataclasses").asdict(row.coverage),
        )
        for row in reader.source_view_coverage(source_view_id, "resolve.symbol_scope")
    )
    parent_index = {parent.ref.id: parent for parent in parent_views}
    context_sources = {}
    for record in observations:
        value = record.get("payload", {})
        if not isinstance(value, Mapping):
            continue
        source_id = value.get("binding_source_view_id")
        pointer = value.get("binding_pointer")
        parent = parent_index.get(source_id)
        if parent is not None and pointer is not None:
            item = next((i for i in parent.items if i["self_ref"] == pointer), None)
            if item is not None:
                context_sources[source_id, pointer] = dict(
                    kind="ancestor_source",
                    source_view_id=source_id,
                    native_product=parent.ref.native_product.values(),
                    projection_digest=parent.ref.projection_digest,
                    item=item,
                    binding_quote=value.get("binding_quote"),
                )
    observations.extend(context_sources.values())
    known_classes = {entity.entity_id: tuple(getattr(entity, "classes", ())) for entity in known}
    return proposal_packet(
        prepared,
        frame,
        guideline=reader.guideline(),
        configuration=raw,
        known_classes=known_classes,
        known_entities=tuple(
            KnownProposalEntity(entity.entity_id, entity.label, entity.aliases) for entity in known
        ),
        macros={
            name: MacroDef(body=body)
            for name, body in (raw.get("math") or {}).get("macros", {}).items()
        },
        native_observations=tuple(observations),
    )


class NativeContextDeclaration(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    symbol: str
    role: Literal["variable", "function"]
    rule_id: str
    source_pointer: str
    recognized_start: int
    recognized_end: int
    scope_pointer: str
    quote: str
    projection_start: int | None = None
    projection_end: int | None = None


class NativeContextPayload(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    source_view_id: int
    native_product: dict[str, Any]
    projection_digest: str
    demand: Literal["context_declarations"] = "context_declarations"
    declarations: tuple[NativeContextDeclaration, ...]
    issues: tuple[str, ...] = ()


def native_context_result(unit: Any, view: Any, cfg: Any, reader: Any) -> UnitResult:
    """Prepare demanded ancestor roles without all-parent M09/M11 or native algebra."""

    from corpus_structure.core.evidence import Segment
    from corpus_structure.core.vocab import SegmentKind

    from .prepared import PreparedMathInput
    from .scope import math_tokens
    from .spans import MathSpan, SpanReading, extract, formula_values

    section = cfg.section()
    pieces = {p["item_ref"]: p for p in view.pieces if p.get("item_ref")}
    primary_scope = _primary_scope(reader, view, cfg.binders, section.native_domain_rules)
    sentences = primary_scope.sentences
    layers = _primary_layers(reader, view)
    health = {o["pointer"]: o["outcome"] for o in view.health.get("formula_outcomes", ())}
    declarations = []
    issues = list(recognition_context_issues(view))
    if not primary_scope.complete:
        issues.append("primary mathematical source cue coverage unavailable")
    blocks = domain_blocks(view, section.native_domain_rules, primary_scope=primary_scope)
    for ordinal, item in enumerate(view.items):
        if item.get("label") != "formula":
            continue
        pointer = item["self_ref"]
        latex = item["text"]
        piece = pieces.get(pointer)
        sentence = (
            None
            if piece is None
            else next(((a, b) for a, b in sentences if a <= piece["start"] < b), None)
        )
        flags = (
            frozenset()
            if piece is None or not primary_scope.complete
            else primary_scope.flags(piece["start"])
        )
        initial, clause, wide = (kind in flags for kind in ("initial", "clause", "section_wide"))
        if health.get(pointer) != "succeeded":
            issues.append("ancestor declaration recognition unavailable: " + pointer)
            continue
        _, scope, _ = _declaration_scope(view, section.native_domain_rules, ordinal, blocks)
        if ":section:" not in scope and not wide:
            continue
        context = prepare_interpretation_context(
            getattr(reader, "prepared", None),
            macros=section.macro_table(),
            constants=section.constants,
        )
        operand = PreparedMathInput(context, latex)
        syntax = _retain_syntax(operand, view, pointer, layers).syntax()
        if syntax.tree is None:
            issues.append("ancestor declaration syntax unavailable: " + pointer)
            continue
        quote = latex if sentence is None else view.text[sentence[0] : sentence[1]]
        for symbol, (a, b) in _heads(syntax):
            declarations.append(
                NativeContextDeclaration(
                    symbol=symbol,
                    role="function",
                    rule_id="function-definition-1",
                    source_pointer=pointer,
                    recognized_start=a,
                    recognized_end=b,
                    scope_pointer=native_topology(view).section(pointer),
                    quote=quote,
                    projection_start=None if sentence is None else sentence[0],
                    projection_end=None if sentence is None else sentence[1],
                )
            )
        if initial or clause or wide:
            reading = operand.interpretation()
            segment = Segment(kind=SegmentKind.MATH_INLINE, start=0, end=len(latex))
            rows = [SpanReading(MathSpan(segment, latex, 0), reading, operand)]
            found = extract(rows)
            token = math_tokens(formula_values(rows), found.mentions, found.relations).get(0)
            if token is not None:
                for mention in token.bound:
                    declarations.append(
                        NativeContextDeclaration(
                            symbol=mention.name,
                            role="variable",
                            rule_id="binder:section_wide"
                            if wide
                            else "binder:initial"
                            if initial
                            else "binder:clause",
                            source_pointer=pointer,
                            recognized_start=mention.start,
                            recognized_end=mention.end,
                            scope_pointer=native_topology(view).section(pointer),
                            quote=quote,
                            projection_start=None if sentence is None else sentence[0],
                            projection_end=None if sentence is None else sentence[1],
                        )
                    )
    payload = NativeContextPayload(
        source_view_id=view.ref.id,
        native_product=view.ref.native_product.values(),
        projection_digest=view.ref.projection_digest,
        declarations=tuple(declarations),
        issues=tuple(issues),
    )
    draft = ObservationDraft(
        kind=ObservationKind.RECORD,
        payload=payload,
        payload_class=NativeContextPayload,
        payload_version="1",
        source_view_id=view.ref.id,
    )
    return UnitResult(
        ref=unit.ref,
        outcome=ObservationOutcome.PRODUCED,
        observations=(draft,),
        coverage=(
            CoverageDraft(
                family="resolve.symbol_scope",
                scope=view.ref.key,
                outcome="partial" if issues or not section.native_domain_rules else "complete",
                reason="ancestor declaration preparation incomplete"
                if issues or not section.native_domain_rules
                else None,
                required_capability="context_declarations",
            ),
        ),
    )


def _stored_parent_candidates(reader: Any, view: Any):
    """Select persisted, forward-applicable declarations once for scopes and demand callers."""
    parents, missing = ancestor_views(reader, view)
    issues = list(missing)
    result = {}
    for parent in sorted(parents, key=lambda v: len(v.ancestors), reverse=True):
        rows = reader.source_observations(
            parent.ref.id, "resolve.symbol_scope", ObservationKind.SCOPE
        )
        coverage = reader.source_view_coverage(parent.ref.id, "resolve.symbol_scope")
        if not coverage or any(row.coverage.outcome != "complete" for row in coverage):
            issues.append("ancestor symbol-scope coverage incomplete: " + parent.ref.key)
        native_order = {item["self_ref"]: n for n, item in enumerate(parent.items)}
        candidates = {}

        def offer(
            symbol,
            role,
            pointer,
            position,
            basis,
            row,
            *,
            native_order=native_order,
            parent=parent,
            candidates=candidates,
        ):
            if pointer not in native_order:
                issues.append(
                    "ancestor declaration pointer outside supplied source: " + str(pointer)
                )
                return
            before = _before_descendant(parent, view, pointer)
            if before is None:
                issues.append("ancestor declaration source order unavailable: " + pointer)
            if before is not True:
                return
            identity = (symbol, role)
            if identity not in candidates or position > candidates[identity][0]:
                candidates[identity] = (
                    position,
                    parent,
                    dict(
                        basis,
                        role=role,
                        preparation_observation=row.observation_key,
                        preparation_hash=row.payload_hash,
                    ),
                )

        for row in rows:
            value = row.payload
            if (
                value.get("outcome") != "resolved"
                or value.get("scope_pointer") != parent.ref.section_pointer
            ):
                continue
            pointer = value.get("binding_pointer")
            if (
                value.get("binding_source_view_id") != parent.ref.id
                or value.get("binding_projection_digest") != parent.ref.projection_digest
            ):
                issues.append(
                    "ancestor binding differs from supplied source pin: " + row.observation_key
                )
                continue
            if pointer is None:
                continue
            offer(
                value["symbol"],
                "variable",
                pointer,
                (native_order.get(pointer, -1), value.get("scope_start") or 0),
                value,
                row,
            )
        for row in reader.source_observations(
            parent.ref.id, "resolve.symbol_scope", ObservationKind.RECORD
        ):
            value = row.payload
            if value.get("demand") != "context_declarations":
                continue
            if (
                value.get("source_view_id") != parent.ref.id
                or value.get("native_product") != parent.ref.native_product.values()
                or value.get("projection_digest") != parent.ref.projection_digest
            ):
                issues.append(
                    "ancestor preparation differs from supplied source pin: " + row.observation_key
                )
                continue
            issues.extend(value.get("issues", ()))
            for declaration in value.get("declarations", ()):
                role = declaration.get("role")
                if role not in {"variable", "function"}:
                    issues.append("ancestor declaration role unsupported: " + str(role))
                    continue
                if declaration.get("scope_pointer") != parent.ref.section_pointer:
                    continue
                pointer = declaration["source_pointer"]
                basis = dict(
                    binding_observation=row.observation_key,
                    binding_pointer=pointer,
                    binding_source_view_id=parent.ref.id,
                    binding_projection_digest=parent.ref.projection_digest,
                    binding_quote=declaration["quote"],
                    scope_pointer=parent.ref.section_pointer,
                    scope_start=declaration.get("projection_start"),
                    scope_end=len(parent.text),
                    recognized_start=declaration["recognized_start"],
                    recognized_end=declaration["recognized_end"],
                    rule_id=declaration["rule_id"],
                    input_role="native_parent_context",
                )
                offer(
                    declaration["symbol"],
                    role,
                    pointer,
                    (native_order.get(pointer, -1), declaration["recognized_start"]),
                    basis,
                    row,
                )
        prepared_functions = {
            basis["binding_pointer"]
            for (_, role), (_, _, basis) in candidates.items()
            if role == "function"
        }
        for item in parent.items:
            text = item.get("text", "")
            if (
                item.get("label") == "formula"
                and "(" in text.partition("=")[0]
                and "=" in text
                and _before_descendant(parent, view, item["self_ref"]) is True
                and item["self_ref"] not in prepared_functions
            ):
                issues.append("ancestor function role preparation unavailable: " + item["self_ref"])
        for identity, (_, owner, value) in candidates.items():
            result.setdefault(identity, (owner, value))
    return result, tuple(dict.fromkeys(issues))


def stored_native_ancestor_declarations(reader: Any, view: Any):
    """Hydrate qualified stored roles for on-demand interpretation; never parse parents."""
    from corpus_structure.semantic.identity import canonical_bytes

    candidates, issues = _stored_parent_candidates(reader, view)
    source = f"source-view:{view.ref.id}:{view.ref.projection_digest}:native-order"
    declarations = []
    for (symbol, role), (parent, basis) in sorted(candidates.items()):
        evidence = dict(
            basis,
            native_product=parent.ref.native_product.values(),
            source_view_id=parent.ref.id,
            projection_digest=parent.ref.projection_digest,
            before_descendant=True,
        )
        declarations.append(
            dict(
                symbol=symbol,
                role=role,
                authority="source",
                source_id=source,
                scope=f"{source}:section:{view.ref.section_pointer}",
                start=0,
                end=len(view.items),
                evidence=canonical_bytes(evidence).decode(),
            )
        )
    return tuple(declarations), issues


def _inherited_bindings(reader: Any, view: Any):
    candidates, issues = _stored_parent_candidates(reader, view)
    return {
        symbol: value for (symbol, role), value in candidates.items() if role == "variable"
    }, issues


@dataclass(frozen=True, slots=True)
class NativeScopeContent:
    """Pure scope-kernel lowering; raw projection text is not forced through legacy NFC custody."""

    canonical_text: str
    document: Segment

    def text(self, segment: Segment) -> str:
        return self.canonical_text[segment.start : segment.end]


def native_scope_result(unit: Any, cfg: Any, ctx: Any) -> UnitResult:
    """Reuse positioned scope kernels on an in-memory lowering of one native section."""
    from types import SimpleNamespace

    from corpus_structure.core.evidence import Segment
    from corpus_structure.core.method import SourceObservationReference
    from corpus_structure.core.payloads import ValuePayload
    from corpus_structure.core.values import Formula, SetValue
    from corpus_structure.core.vocab import MathKind, SegmentKind

    kind_of = {
        MathKind.FORMULA: "formula",
        MathKind.RELATION: "relation",
        MathKind.MEMBERSHIP: "member",
        MathKind.SET: "set_expr",
        MathKind.LIST: "list",
    }
    from .scope import resolve_scopes
    from .spans import MathRelation, SpanValue, SymbolMention

    view = ctx.reader.source_view(unit.ref.unit_id)
    if getattr(unit, "context_only", False) or not getattr(view.ref, "analysis_eligible", True):
        return native_context_result(unit, view, cfg, ctx.reader)
    if cfg.binders is None:
        raise ValueError("native symbol scope requires resolved primary binder configuration")
    section = cfg.section()
    primary_scope = _primary_scope(ctx.reader, view, cfg.binders, section.native_domain_rules)
    domains = domain_blocks(view, section.native_domain_rules, primary_scope=primary_scope)
    native = {item["self_ref"]: item for item in view.items if item.get("label") == "formula"}
    pieces_by_ref = {p["item_ref"]: p for p in view.pieces if p.get("item_ref")}
    selected = {
        pointer: SimpleNamespace(
            prepared=SimpleNamespace(latex=item["text"]),
            projected_start=pieces_by_ref[pointer]["start"]
            if pointer in pieces_by_ref
            and view.text[pieces_by_ref[pointer]["start"] : pieces_by_ref[pointer]["end"]]
            == item["text"]
            else None,
        )
        for pointer, item in native.items()
    }
    math_segments = {}
    for pointer, reading in selected.items():
        start = reading.projected_start
        if start is not None:
            math_segments[pointer] = Segment(
                kind=SegmentKind.MATH_INLINE,
                start=start,
                end=start + len(reading.prepared.latex),
                attrs={"native_pointer": pointer},
            )
    # Native text/formula items may be fragments of the same mathematical sentence.
    # Partition only on attributed statement scopes, not on every PDF item/page boundary.
    topology = native_topology(view)
    cuts = sorted(
        {
            0,
            len(view.text),
            *(value for bounds in topology.bounds.values() for value in bounds),
            *(value for start, end, _, _ in domains for value in (start, end)),
        }
    )
    paragraphs = [
        Segment(
            kind=SegmentKind.PARAGRAPH,
            start=a,
            end=b,
            children=tuple(
                node for node in math_segments.values() if a <= node.start and node.end <= b
            ),
        )
        for a, b in pairwise(cuts)
        if a < b
    ]

    def paragraph_section(paragraph):
        owners = {
            topology.section(piece["item_ref"])
            for piece in view.pieces
            if piece.get("item_ref") in topology.chains
            and piece["start"] < paragraph.end
            and paragraph.start < piece["end"]
        }
        if len(owners) > 1:
            raise ValueError("native scope block crosses section membership boundaries")
        return next(iter(owners), topology.root)

    content_by_section = {section: [] for section in topology.bounds}
    used = set()
    for start, end, pointer, rule in domains:
        owner = topology.section(pointer)
        children = tuple(
            paragraph
            for paragraph in paragraphs
            if start <= paragraph.start
            and paragraph.end <= end
            and paragraph_section(paragraph) == owner
        )
        used.update(id(p) for p in children)
        content_by_section[owner].append(
            Segment(
                kind=SegmentKind.UNIT,
                start=start,
                end=end,
                attrs={"native_pointer": pointer, "recognition_rule": rule.rule_id},
                children=children,
            )
        )
    for paragraph in paragraphs:
        if id(paragraph) not in used:
            content_by_section[paragraph_section(paragraph)].append(paragraph)
    section_segments = {}

    def section_segment(pointer):
        start, end = topology.bounds[pointer]
        children = list(content_by_section[pointer])
        children.extend(
            section_segment(child)
            for child, parent in topology.section_parents.items()
            if parent == pointer and child in topology.bounds
        )
        segment = Segment(
            kind=SegmentKind.DOCUMENT if pointer == topology.root else SegmentKind.SECTION,
            start=start,
            end=end,
            attrs={"native_pointer": pointer},
            children=tuple(sorted(children, key=lambda child: (child.start, child.end))),
        )
        section_segments[pointer] = segment
        return segment

    content = NativeScopeContent(canonical_text=view.text, document=section_segment(topology.root))
    # This value is solely a pure-kernel lowering: it is never stored as kb.rendition.
    stored = ctx.reader.source_observations(view.ref.id, "extract.math", ObservationKind.MENTION)
    values = []
    for row in ctx.reader.source_observations(
        view.ref.id, "normalize.formula", ObservationKind.VALUE
    ):
        pointer = getattr(row, "native_pointer", None)
        if pointer is None:
            continue
        if pointer in math_segments:
            value = ValuePayload.model_validate(row.payload)
            if not isinstance(value.value, Formula | SetValue):
                raise ValueError("native mathematical value report has a nonmathematical value")
            values.append(
                SpanValue(
                    math_segments[pointer],
                    value.value,
                    kind_of.get(value.math_kind) if isinstance(value.math_kind, MathKind) else None,
                    value.parse_error if isinstance(value.parse_error, str) else None,
                )
            )
    mentions = []
    for row in stored:
        payload = row.payload
        pointer = payload["source_pointer"]
        if pointer not in math_segments:
            continue
        offset = selected[pointer].projected_start
        info = payload["math"]
        mentions.append(
            SymbolMention(
                math_segments[pointer],
                offset + payload["recognized_start"],
                offset + payload["recognized_end"],
                info["name"],
                info["base"],
                info.get("sub"),
                info.get("sup"),
                info.get("constant", False),
                info.get("in_subscript_of"),
            )
        )
    relations = []
    for row in ctx.reader.source_observations(
        view.ref.id, "extract.math", ObservationKind.RELATION
    ):
        payload = row.payload
        pointer = payload["source_pointer"]
        if pointer in math_segments:
            offset = selected[pointer].projected_start
            relations.append(
                MathRelation(
                    math_segments[pointer],
                    payload["label"],
                    tuple(offset + x for x in payload["recognized_head"]),
                    tuple(offset + x for x in payload["recognized_tail"]),
                    "",
                )
            )
    pointers = {id(segment): pointer for pointer, segment in math_segments.items()}
    section_at = {
        mention.start: section_segments[topology.section(pointers[id(mention.segment)])]
        for mention in mentions
    }
    scopes = resolve_scopes(
        content,
        values,
        mentions,
        relations,
        section.macro_table(),
        primary_scope=primary_scope,
        sections_by_position=section_at,
    )
    locations = {}
    for row in stored:
        payload = row.payload
        locations[
            (
                payload.get("source_pointer"),
                payload.get("recognized_start"),
                payload.get("recognized_end"),
            )
        ] = row
    by_position = {
        (
            pointer,
            mention.start - selected[pointer].projected_start,
            mention.end - selected[pointer].projected_start,
        ): scope
        for scope in scopes
        for mention in (scope.mention,)
        if (pointer := pointers.get(id(mention.segment))) is not None
    }
    inherited, ancestor_issues = _inherited_bindings(ctx.reader, view)
    drafts: list[ObservationDraft[Any]] = []
    for row in stored:
        raw = row.payload
        if raw["math"].get("constant"):
            continue
        pointer = raw["source_pointer"]
        start, end = raw["recognized_start"], raw["recognized_end"]
        scope = by_position.get((pointer, start, end))
        site = None if scope is None else scope.site
        binding = None
        if site is not None:
            bp = pointers[id(site.mention.segment)]
            offset = selected[bp].projected_start
            binding = locations.get((bp, site.mention.start - offset, site.mention.end - offset))
        parent_binding = inherited.get(raw["math"]["name"]) if site is None else None
        payload = NativeScopePayload(
            source_pointer=pointer,
            recognized_start=start,
            recognized_end=end,
            symbol=raw["math"]["name"],
            outcome="resolved" if site is not None and binding is not None else "unresolved",
            binding_observation=None if binding is None else binding.observation_key,
            binding_pointer=None if site is None else pointers[id(site.mention.segment)],
            binding_source_view_id=view.ref.id if binding is not None else None,
            binding_projection_digest=view.ref.projection_digest if binding is not None else None,
            binding_quote=None
            if site is None
            else view.text[site.sentence.start : site.sentence.end],
            scope_source_view_id=view.ref.id if site is not None else None,
            scope_projection_digest=view.ref.projection_digest if site is not None else None,
            extent=None
            if site is None
            else "section"
            if site.scope.kind is SegmentKind.DOCUMENT
            else str(site.extent),
            scope_pointer=(
                site.scope.attrs.get("native_pointer")
                if site is not None and isinstance(site.scope.attrs.get("native_pointer"), str)
                else None
            ),
            scope_start=None if site is None else site.start,
            scope_end=None if site is None else site.end,
            reason=None
            if site is not None and binding is not None
            else "native binding unavailable or unresolved",
        )
        refs = [SourceObservationReference(row.observation_key, "mention")]
        if parent_binding is not None:
            owner, basis = parent_binding
            payload = payload.model_copy(
                update=dict(
                    outcome="resolved",
                    reason=None,
                    binding_observation=basis["binding_observation"],
                    binding_pointer=basis["binding_pointer"],
                    binding_source_view_id=basis.get("binding_source_view_id", owner.ref.id),
                    binding_projection_digest=basis.get(
                        "binding_projection_digest", owner.ref.projection_digest
                    ),
                    binding_quote=basis.get("binding_quote"),
                    scope_pointer=basis["scope_pointer"],
                    scope_source_view_id=owner.ref.id,
                    scope_projection_digest=owner.ref.projection_digest,
                    scope_start=basis.get("scope_start"),
                    scope_end=basis.get("scope_end"),
                    extent="section",
                )
            )
            refs.append(
                SourceObservationReference(
                    basis["binding_observation"], basis.get("input_role", "binding_site")
                )
            )
        if binding is not None:
            refs.append(SourceObservationReference(binding.observation_key, "binding_site"))
        offset = selected[pointer].projected_start if pointer in selected else None
        drafts.append(
            ObservationDraft(
                kind=ObservationKind.SCOPE,
                payload=payload,
                payload_class=NativeScopePayload,
                payload_version="3",
                source_view_id=view.ref.id,
                native_pointer=pointer,
                recognized_span=(start, end),
                projected_span=None if offset is None else (offset + start, offset + end),
                input_refs=tuple(refs),
            )
        )
    for start, end, pointer, rule in domains:
        payload = NativeDomainPayload(
            rule_id=rule.rule_id,
            pattern=rule.pattern,
            statement_kind=rule.statement_kind,
            scope_role=rule.scope_role,
            source_pointer=pointer,
            start=start,
            end=end,
        )
        drafts.append(
            ObservationDraft(
                kind=ObservationKind.AUTHOR_MARKUP,
                payload=payload,
                payload_class=NativeDomainPayload,
                payload_version="3",
                source_view_id=view.ref.id,
                native_pointer=pointer,
                projected_span=(start, end),
            )
        )
    incomplete = any(
        d.kind is ObservationKind.SCOPE and d.payload.outcome == "unresolved" for d in drafts
    )
    upstream = ctx.reader.source_view_coverage(view.ref.id, "extract.math")
    incomplete = (
        incomplete
        or bool(ancestor_issues)
        or not section.native_domain_rules
        or not upstream
        or any(r.coverage.outcome != "complete" for r in upstream)
    )
    return UnitResult(
        ref=unit.ref,
        outcome=ObservationOutcome.PRODUCED if drafts else ObservationOutcome.EMPTY,
        observations=tuple(drafts),
        coverage=(
            CoverageDraft(
                family="resolve.symbol_scope",
                scope=view.ref.key,
                outcome="partial" if incomplete else "complete",
                reason="native source scope or upstream recognition is incomplete"
                if incomplete
                else None,
                required_capability="interpretation",
            ),
        ),
    )
