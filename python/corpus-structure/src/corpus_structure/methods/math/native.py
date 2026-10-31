"""Source-view mathematical consumers over qualified native occurrences.

The source view is the execution unit; recognized LaTeX offsets remain occurrence-local.
No PDF paragraph, page, section or formula is persisted as an invented rendition.
"""
from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict

from corpus_structure.core.method import CoverageDraft, ObservationDraft, UnitResult
from corpus_structure.core.vocab import ObservationKind, ObservationOutcome, ParseOutcome
from corpus_structure.semantic.analysis_contracts import prepare_interpretation_context

from . import grammar
from .pdf import FormulaOccurrence
from .source_context import _heads


class NativeSymbolPayload(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    label: Literal["symbol"] = "symbol"
    text: str
    math: dict[str, Any]
    source_pointer: str
    recognized_start: int
    recognized_end: int


@dataclass(frozen=True)
class NativeReading:
    pointer: str
    prepared: Any
    result: grammar.MathResult
    projected_start: int | None


def readings(view: Any, cfg: Any, reader: Any) -> tuple[NativeReading, ...]:
    """Prepare one ordered native input universe once per compatible operation batch."""
    from .methods import MathReadingsBatch

    batch = getattr(reader, "math_readings_batch", None)
    if batch is None:
        batch = MathReadingsBatch()
        reader.math_readings_batch = batch
    batch.bind(reader)
    section = cfg.section()
    key = (view.ref.id, view.ref.projection_digest, cfg.parse_seconds,
           tuple(section.constants))
    if key in batch.native:
        return batch.native[key]
    health = {row["pointer"]: row["outcome"] for row in view.health.get("formula_outcomes", ())}
    pieces = {piece["item_ref"]: piece for piece in view.pieces if piece.get("item_ref")}
    definitions: list[dict[str, Any]] = []
    out: list[NativeReading] = []
    for item in view.items:
        if item.get("label") != "formula":
            continue
        pointer = item["self_ref"]
        if health.get(pointer) != "succeeded":
            continue
        text = item["text"]
        piece = pieces.get(pointer)
        start = None
        if piece is not None and view.text[piece["start"]:piece["end"]] == text:
            start = piece["start"]
        context = prepare_interpretation_context(
            getattr(reader, "prepared", None), macros={}, constants=section.constants,
            source_id=f"source-view:{view.ref.id}:{view.ref.projection_digest}",
            declarations=definitions, demand="occurrences")
        operand = FormulaOccurrence(view.ref.native_product.content_digest, pointer, text,
                                    item.get("orig", ""), "succeeded").prepare(context).operand
        operand = replace(operand, seconds=cfg.parse_seconds)
        recognized = operand.syntax()
        # The admitted native rule supplies the mathematical head; visual adjacency never
        # turns an arbitrary identifier into a function declaration.
        if context.allow_local_definitions:
            for symbol, extent in _heads(recognized):
                definitions.append(dict(symbol=symbol, role="function", authority="source",
                    evidence=f"{pointer}:{extent[0]}:{extent[1]}",
                    source_id=context.source_id))
        result = operand.symbolic_reading()
        out.append(NativeReading(pointer, operand, result, start))
    batch.native[key] = tuple(out)
    return tuple(out)


def native_result(unit: Any, cfg: Any, ctx: Any, method: str) -> UnitResult:
    from corpus_structure.core.payloads import ValuePayload
    from .spans import SpanReading, MathSpan, formula_values
    from corpus_structure.core.evidence import Segment
    from corpus_structure.core.vocab import SegmentKind

    view = ctx.reader.source_view(unit.ref.unit_id)
    selected = readings(view, cfg, ctx.reader)
    drafts = []
    for reading in selected:
        text = reading.prepared.latex
        projected = None if reading.projected_start is None else (
            reading.projected_start, reading.projected_start + len(text))
        if method == "normalize.formula":
            segment = Segment(kind=SegmentKind.MATH_DISPLAY, start=0, end=len(text))
            value = formula_values([SpanReading(MathSpan(segment, text, 0), reading.result,
                                               reading.prepared)])[0]
            fields = {"value": value.value}
            if value.parse_error is not None:
                fields["parse_error"] = value.parse_error
            if value.math_kind is not None:
                fields["math_kind"] = value.math_kind
            payload = ValuePayload(**fields)
            drafts.append(ObservationDraft(kind=ObservationKind.VALUE, payload=payload,
                payload_class=ValuePayload, payload_version="3", source_view_id=view.ref.id,
                native_pointer=reading.pointer, projected_span=projected,
                recognized_span=(0, len(text))))
        else:
            for symbol in reading.result.occurrences:
                payload = NativeSymbolPayload(text=text[symbol.start:symbol.end],
                    math=dict(name=symbol.name, base=symbol.base, sub=symbol.sub, sup=symbol.sup,
                              constant=symbol.constant, in_subscript_of=symbol.in_subscript_of),
                    source_pointer=reading.pointer,
                    recognized_start=symbol.start, recognized_end=symbol.end)
                location = None if reading.projected_start is None else (
                    reading.projected_start + symbol.start, reading.projected_start + symbol.end)
                drafts.append(ObservationDraft(kind=ObservationKind.MENTION, payload=payload,
                    payload_class=NativeSymbolPayload, payload_version="3", source_view_id=view.ref.id,
                    native_pointer=reading.pointer, projected_span=location,
                    recognized_span=(symbol.start, symbol.end)))
    recognized = {r.pointer for r in selected}
    formulas = {i["self_ref"] for i in view.items if i.get("label") == "formula"}
    complete = formulas <= recognized and all(r.result.status == ParseOutcome.OK for r in selected)
    coverage = tuple(CoverageDraft(family=method, scope=view.ref.key,
        outcome="complete" if complete and view.health.get("inline_coverage") == "complete"
                and view.health.get("cell_coverage") == "complete" else "partial",
        reason=None if complete and view.health.get("inline_coverage") == "complete"
                and view.health.get("cell_coverage") == "complete"
               else "native recognition/interpretation coverage is incomplete",
        required_capability="interpretation") for _ in (0,))
    return UnitResult(ref=unit.ref,
        outcome=ObservationOutcome.PRODUCED if drafts else ObservationOutcome.EMPTY,
        observations=tuple(drafts), coverage=coverage)


class NativeAnalysisPayload(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    source_view_id: int
    native_product: dict[str, Any]
    projection_digest: str
    recipe_digest: str
    demand: str
    items: tuple[dict[str, Any], ...]


def native_request_analysis(view: Any, prepared: Any, demand: str, pointer: str | None = None,
                            question: str | None = None, predicate: str | None = None,
                            seconds: float = grammar.PARSE_SECONDS) -> NativeAnalysisPayload:
    """Finite native demand kernel; no converter, database or stronger extraction entrypoint."""
    import dataclasses
    import sympy
    from lark import Tree, Token
    from .prepared import PreparedMathInput
    from .transform import NotRepresentable

    allowed = {"lexical", "structure", "syntax", "interpretation", "occurrences", "symbolic", "scientific"}
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

    def tree_value(node):
        if isinstance(node, Token):
            return dict(token=node.type, text=str(node), start=node.start_pos, end=node.end_pos)
        if isinstance(node, Tree):
            from ._tree import span
            extent = span(node)
            return dict(rule=str(node.data), extent=extent,
                        children=[tree_value(child) for child in node.children])
        raise TypeError("unsupported positioned syntax node")

    def syntax_value(result):
        return dict(outcome=result.status.value, kind=result.kind, tail=result.tail,
            failure=None if result.failure is None else dataclasses.asdict(result.failure),
            syntax=None if result.tree is None else tree_value(result.tree),
            occurrences=[dataclasses.asdict(o) for o in result.occurrences],
            declarations=[dataclasses.asdict(d) for d in result.declarations], notes=list(result.notes))

    definitions = []
    results = []
    for item in formulas:
        ref = item["self_ref"]
        outcome = health.get(ref, "unknown")
        selected = pointer is None or ref == pointer
        if outcome != "succeeded":
            if selected:
                results.append(dict(pointer=ref, orig=item.get("orig", ""), recognized_latex=item["text"],
                                    recognition_health=outcome, availability="unavailable"))
            continue
        context = prepare_interpretation_context(prepared, macros={},
            source_id=f"source-view:{view.ref.id}:{view.ref.projection_digest}",
            declarations=definitions, demand=demand)
        operand = PreparedMathInput(context, item["text"], seconds=seconds)
        # Only contextual demands need prior mathematical declaration recognition.
        contextual = demand in {"interpretation", "occurrences", "symbolic", "scientific"}
        if contextual and context.allow_local_definitions and "(" in item["text"].partition("=")[0] and "=" in item["text"]:
            for symbol, extent in _heads(operand.syntax()):
                definitions.append(dict(symbol=symbol, role="function", authority="source",
                    evidence=f"{ref}:{extent[0]}:{extent[1]}", source_id=context.source_id))
        if not selected:
            continue
        value = dict(pointer=ref, orig=item.get("orig", ""), recognized_latex=item["text"],
            recognition_health=outcome, availability="available", context_basis=context.stage_key(
                demand, **({"conditions": [dataclasses.asdict(c) for c in operand.definedness()],
                           "precision": {"mode": "exact-symbolic"}, "sampling": {"requested": False},
                           "decision_policy": {"question": question, "predicate": predicate}}
                          if demand == "scientific" else {})))
        if demand == "lexical":
            value["lexical"] = [dict(kind=t.kind, text=t.text, start=t.start, end=t.end)
                                for t in operand.lexical()]
        elif demand == "structure":
            capture = operand.structure()
            value["structure"] = dict(outcome=capture.structure_outcome,
                nodes=[dataclasses.asdict(n) for n in capture.nodes], issues=capture.issues)
        elif demand == "syntax":
            value.update(syntax_value(operand.syntax()))
        else:
            value.update(syntax_value(operand.interpretation()))
            if demand == "symbolic":
                try:
                    native = operand.symbolic_value()
                    value["symbolic"] = dict(format="sympy-srepr-1", expression=sympy.srepr(native))
                except (NotRepresentable, grammar.NotParsed, grammar.Ambiguous) as error:
                    value["symbolic"] = dict(outcome="unsupported", diagnostic=str(error))
                value["definedness"] = dataclasses.asdict(operand.definedness_result())
            if demand == "scientific":
                assessment = operand.assess(question, predicate=predicate)
                value["assessment"] = dict(question=assessment.question, outcome=assessment.outcome,
                    value=None if assessment.value is None else sympy.srepr(assessment.value),
                    conditions=[dataclasses.asdict(c) for c in assessment.conditions],
                    diagnostic=assessment.diagnostic, coverage=assessment.coverage)
        value["stages"] = {name: dataclasses.asdict(operand.state(name)) for name in allowed}
        results.append(value)
    return NativeAnalysisPayload(source_view_id=view.ref.id,
        native_product=view.ref.native_product.values(), projection_digest=view.ref.projection_digest,
        recipe_digest=view.ref.recipe_digest, demand=demand, items=tuple(results))


def native_proposal_packet(reader: Any, source_view_id: int, prepared: Any,
                           configuration: Any, *, known: tuple[Any, ...] = ()):
    """Build one intact section packet from pinned native context and stored upstream facts."""
    from corpus_structure.ingest.sentences import Block, SentenceConfig, split
    from corpus_structure.semantic.proposals import KnownProposalEntity, native_source_frame, proposal_packet

    view = reader.source_view(source_view_id)
    native = {item["self_ref"]: item for item in view.items}
    mathematical = tuple((piece["start"], piece["end"]) for piece in view.pieces
        if piece.get("item_ref") in native and native[piece["item_ref"]].get("label") == "formula")
    block = Block(view.text, mathematical, (), ())
    extents = split([block], SentenceConfig(), layouts=[view.layout])[0]
    frame = native_source_frame(view, [(f"s{index+1}", start, end)
                                       for index, (start, end) in enumerate(extents)])
    observations = []
    for kind in (ObservationKind.SCOPE, ObservationKind.AUTHOR_MARKUP):
        for row in reader.source_observations(source_view_id, "resolve.symbol_scope", kind):
            observations.append(dict(observation_key=row.observation_key,
                kind=str(kind), payload=dict(row.payload)))
    observations.extend(dict(kind="coverage", family="resolve.symbol_scope",
        task_id=row.task_id, release_id=row.release_id, coverage=__import__('dataclasses').asdict(row.coverage))
        for row in reader.source_view_coverage(source_view_id, "resolve.symbol_scope"))
    known_classes = {entity.entity_id: tuple(getattr(entity, "classes", ())) for entity in known}
    return proposal_packet(prepared, frame, guideline=reader.guideline(),
        configuration=configuration, known_classes=known_classes,
        known_entities=tuple(KnownProposalEntity(entity.entity_id, entity.label, entity.aliases)
                             for entity in known),
        macros={}, native_observations=tuple(observations))
