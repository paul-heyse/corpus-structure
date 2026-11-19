"""Shared mathematical kernels over explicit native source columns and retained syntax.

Current declared operations own source selection, provenance and authority. These
kernels preserve occurrence positions, tree scope, interpretation and diagnostics.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from itertools import pairwise
from typing import Any

from corpus_structure.core.evidence import Segment
from corpus_structure.semantic.source_types import ParseOutcome

from . import grammar
from .source_context import _heads


def domain_blocks_columns(*, root, text, items, ancestors, pieces, rules, primary_scope=None):
    from .native_topology import prepare_native_topology_columns

    """Combine retained source-marker candidates with actual native section topology."""
    if not rules:
        return ()
    if primary_scope is None or not primary_scope.complete:
        raise ValueError("native domain scopes require complete primary source-marker coverage")
    topology = prepare_native_topology_columns(
        root=root, text=text, items=items, ancestors=ancestors, pieces=pieces
    )
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
    topology = prepare_native_topology_columns(
        root=root, text=text, items=items, ancestors=ancestors, pieces=pieces
    )
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


def before_descendant_columns(
    *,
    parent_items,
    parent_ancestors,
    child_items,
    child_ancestors,
    ancestor,
    child_pointer,
    pointer,
) -> bool | None:
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


@dataclass(frozen=True)
class NativeReading:
    pointer: str
    prepared: Any
    result: grammar.MathResult
    projected_start: int | None
    context_issues: tuple[str, ...] = ()


def prepare_native_readings(
    *,
    items,
    text,
    pieces,
    health,
    section,
    seconds,
    source,
    topology,
    inherited,
    context_issues,
    blocks,
    occurrence,
    retain_syntax,
    selected=lambda item: True,
    check_active=lambda: None,
    prepare_context,
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


def analyze_native_operand(
    operand,
    *,
    demand,
    pointer,
    original,
    recognition_health,
    context_issues,
    context_coverage,
    retained_inventory,
    question: str | None = None,
    predicate: str | None = None,
):
    """Original finite per-operand projection, shared by target and sealed readers."""
    import dataclasses

    import sympy

    from corpus_structure.semantic.math_context import scientific_question_rule

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
    if demand not in allowed or (demand == "scientific" and question is None):
        raise ValueError("native mathematical analysis requires its exact demand/question")
    context = operand.context
    question_rule = None
    if demand == "scientific":
        if question is None:
            raise ValueError("scientific demand requires its explicit question")
        question_rule = scientific_question_rule(context.profile, question)
    value = dict(
        pointer=pointer,
        orig=original,
        recognized_latex=operand.latex,
        primary_input=operand._primary_input,
        recognition_health=recognition_health,
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
        coverage=context_coverage,
        issues=context_issues,
    )
    if demand in {"lexical", "structure"}:
        inventory = retained_inventory()
        if demand == "lexical":
            value["lexical"] = inventory["lexical"]
        else:
            value["structure"] = {key: item for key, item in inventory.items() if key != "lexical"}
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
    return value


@dataclass(frozen=True, slots=True)
class NativeScopeContent:
    """Pure scope-kernel lowering; raw projection text is not forced through legacy NFC custody."""

    canonical_text: str
    document: Segment

    def text(self, segment: Segment) -> str:
        return self.canonical_text[segment.start : segment.end]


def native_scope_layout(*, root, text, items, ancestors, pieces, domains=()):
    """Lower original source columns once for both admitted and historical scope readers."""
    from types import SimpleNamespace

    from corpus_structure.core.evidence import Segment
    from corpus_structure.semantic.source_types import SegmentKind

    from .native_topology import prepare_native_topology_columns

    native = {item["self_ref"]: item for item in items if item.get("label") == "formula"}
    pieces_by_ref = {p["item_ref"]: p for p in pieces if p.get("item_ref")}
    selected = {
        pointer: SimpleNamespace(
            prepared=SimpleNamespace(latex=item["text"]),
            projected_start=pieces_by_ref[pointer]["start"]
            if pointer in pieces_by_ref
            and text[pieces_by_ref[pointer]["start"] : pieces_by_ref[pointer]["end"]]
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
    topology = prepare_native_topology_columns(
        root=root, text=text, items=items, ancestors=ancestors, pieces=pieces
    )
    cuts = sorted(
        {
            0,
            len(text),
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
            for piece in pieces
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

    content = NativeScopeContent(canonical_text=text, document=section_segment(topology.root))
    return content, math_segments, selected, topology, section_segments


def analysis_failure(analysis) -> str | None:
    """A failed attempt is never promoted to a reusable available capability."""
    if analysis is None:
        return None
    for item in analysis.items:
        failure = item.get("failure")
        if isinstance(failure, dict) and failure.get("category") == "timeout":
            return "native mathematical request exceeded its budget"
        for stage in item.get("stages", {}).values():
            if stage.get("work") == "failed":
                return stage.get("diagnostic") or "native mathematical stage failed"
    return None
