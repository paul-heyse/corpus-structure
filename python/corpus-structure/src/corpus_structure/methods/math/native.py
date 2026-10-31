"""Source-view mathematical consumers over qualified native occurrences.

The source view is the execution unit; recognized LaTeX offsets remain occurrence-local.
No PDF paragraph, page, section or formula is persisted as an invented rendition.
"""
from __future__ import annotations

from dataclasses import dataclass, replace
from collections.abc import Mapping
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict

from corpus_structure.core.method import CoverageDraft, ObservationDraft, UnitResult
from corpus_structure.core.vocab import ObservationKind, ObservationOutcome, ParseOutcome
from corpus_structure.semantic.analysis_contracts import prepare_interpretation_context

from . import grammar
from .pdf import FormulaOccurrence
from .source_context import _heads


class NativeDomainRule(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    rule_id: str
    pattern: str
    statement_kind: str
    scope_role: Literal["statement", "proof", "solution", "exercise"]


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


def domain_blocks(view: Any, rules: tuple[NativeDomainRule, ...]):
    """Released pattern matches are attributed local observations, never author truth."""
    import re
    if len({rule.rule_id for rule in rules}) != len(rules):
        raise ValueError("native domain recognition rule identities must be unique")
    patterns = [(rule, re.compile(rule.pattern)) for rule in rules]
    native = {item["self_ref"]: item for item in view.items}
    found = []
    for piece in view.pieces:
        pointer = piece.get("item_ref")
        item = native.get(pointer)
        if item is None or piece["start"] == piece["end"]:
            continue
        matches = [rule for rule, pattern in patterns if pattern.search(item.get("text", ""))]
        if len(matches) > 1:
            raise ValueError("native domain item matches conflicting released recognition rules")
        if matches:
            found.append((piece["start"], pointer, matches[0]))
    found.sort()
    return tuple((start, found[index+1][0] if index+1 < len(found) else len(view.text), pointer, rule)
                 for index, (start, pointer, rule) in enumerate(found))


def _declaration_scope(view: Any, rules: tuple[NativeDomainRule,...], ordinal: int):
    """Source item order and attributed statement boundaries constrain forward roles."""
    source = f"source-view:{view.ref.id}:{view.ref.projection_digest}:native-order"
    if not rules:
        # Without a qualified local-boundary policy, do not invent cross-item applicability.
        return source, f"{source}:item:{ordinal}", ordinal+1
    positions={item["self_ref"]:n for n,item in enumerate(view.items)}
    owner=f"{source}:section:{view.ref.section_pointer}"
    end=len(view.items)
    for _,_,pointer,rule in domain_blocks(view,rules):
        start=positions[pointer]
        if start>ordinal:
            end=start
            break
        owner=f"{source}:statement:{pointer}:{rule.rule_id}"
    return source,owner,end


def _before_descendant(parent: Any, child: Any, pointer: str) -> bool | None:
    """Prove relative order from retained native containment, not collection indices."""
    nodes={item["self_ref"]:item for item in (*parent.items,*parent.ancestors,*child.items,*child.ancestors)}
    ancestor=parent.ref.section_pointer
    root=nodes.get(ancestor)
    if root is None:
        return None
    def branch(ref):
        seen=set()
        while ref!=ancestor:
            if ref in seen or ref not in nodes:
                return None
            seen.add(ref)
            owner=(nodes[ref].get("parent") or {}).get("$ref")
            if owner==ancestor:
                return ref
            if owner is None:
                return None
            ref=owner
        return None
    source,target=branch(pointer),branch(child.ref.section_pointer)
    order=[ref["$ref"] for ref in root.get("children",())]
    if source not in order or target not in order:
        return None
    return order.index(source)<order.index(target)


def ancestor_views(reader: Any, view: Any):
    required={item["self_ref"] for item in view.ancestors if item.get("label") in {"section","chapter"}}
    select=getattr(reader,"ancestor_source_views",None)
    refs=select(view.ref.id) if select is not None else [ref for ref in reader.source_views()
        if ref.section_pointer in required and ref.native_product==view.ref.native_product]
    parents=tuple(reader.source_view(ref.id) for ref in refs)
    missing=required-{parent.ref.section_pointer for parent in parents}
    return parents,tuple("ancestor source context unavailable: "+pointer for pointer in sorted(missing))


def native_ancestor_declarations(reader: Any, view: Any, rules: tuple[NativeDomainRule,...],
                                seconds: float=grammar.PARSE_SECONDS):
    """Prepare attributable forward-only function roles from authorized native ancestor views."""
    from corpus_structure.semantic.identity import canonical_bytes
    from .prepared import PreparedMathInput
    parents,missing=ancestor_views(reader,view)
    issues=list(missing)
    declarations=[]
    source=f"source-view:{view.ref.id}:{view.ref.projection_digest}:native-order"
    for parent in parents:
        health={item["pointer"]:item["outcome"] for item in parent.health.get("formula_outcomes",())}
        for ordinal,item in enumerate(parent.items):
            if item.get("label")!="formula" or "(" not in item.get("text","").partition("=")[0] or "=" not in item["text"]:
                continue
            before=_before_descendant(parent,view,item["self_ref"])
            if before is None:
                issues.append("ancestor declaration source order unavailable: "+item["self_ref"])
            if before is not True:
                continue
            _,scope,_=_declaration_scope(parent,rules,ordinal)
            if ":section:" not in scope:
                continue
            if health.get(item["self_ref"])!="succeeded":
                issues.append("ancestor function declaration recognition unavailable: "+item["self_ref"])
                continue
            context=prepare_interpretation_context(getattr(reader,"prepared",None),macros={})
            syntax=PreparedMathInput(context,item["text"],seconds=seconds).syntax()
            if syntax.tree is None:
                issues.append("ancestor function declaration syntax unavailable: "+item["self_ref"])
            for name,(start,end) in _heads(syntax):
                declarations.append(dict(symbol=name,role="function",authority="source",source_id=source,
                    scope=f"{source}:section:{view.ref.section_pointer}",start=0,end=len(view.items),
                    evidence=canonical_bytes(dict(rule="function-definition-1",
                        native_product=parent.ref.native_product.values(),source_view_id=parent.ref.id,
                        projection_digest=parent.ref.projection_digest,pointer=item["self_ref"],
                        recognized_start=start,recognized_end=end,before_descendant=True)).decode()))
    return tuple(declarations),tuple(issues)


class NativeSymbolPayload(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    label: Literal["symbol"] = "symbol"
    text: str
    math: dict[str, Any]
    source_pointer: str
    recognized_start: int
    recognized_end: int
    context_basis: tuple[dict[str,Any],...] = ()
    context_issues: tuple[str,...] = ()


class NativeRelationPayload(BaseModel):
    model_config = ConfigDict(frozen=True,extra="forbid")
    label: str
    source_pointer: str
    recognized_head: tuple[int,int]
    recognized_tail: tuple[int,int]


@dataclass(frozen=True)
class NativeReading:
    pointer: str
    prepared: Any
    result: grammar.MathResult
    projected_start: int | None
    context_issues: tuple[str,...] = ()


def readings(view: Any, cfg: Any, reader: Any) -> tuple[NativeReading, ...]:
    """Prepare one ordered native input universe once per compatible operation batch."""
    from .methods import MathReadingsBatch

    batch = getattr(reader, "math_readings_batch", None)
    if batch is None:
        batch = MathReadingsBatch()
        reader.math_readings_batch = batch
    batch.bind(reader)
    section = cfg.section()
    seconds = getattr(cfg,"parse_seconds",grammar.PARSE_SECONDS)
    key = (view.ref.id, view.ref.projection_digest, seconds,
           section.model_dump_json())
    if key in batch.native:
        return batch.native[key]
    health = {row["pointer"]: row["outcome"] for row in view.health.get("formula_outcomes", ())}
    pieces = {piece["item_ref"]: piece for piece in view.pieces if piece.get("item_ref")}
    inherited,context_issues=native_ancestor_declarations(reader,view,section.native_domain_rules,seconds)
    definitions: list[dict[str, Any]] = list(inherited)
    out: list[NativeReading] = []
    for ordinal,item in enumerate(view.items):
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
        source_id,scope,end = _declaration_scope(view,section.native_domain_rules,ordinal)
        context = prepare_interpretation_context(
            getattr(reader, "prepared", None), macros={}, constants=section.constants,
            source_id=source_id,scope=scope,offset=ordinal,
            scope_chain=(f"{source_id}:section:{view.ref.section_pointer}",),
            declarations=definitions, demand="occurrences")
        operand = FormulaOccurrence(view.ref.native_product.content_digest, pointer, text,
                                    item.get("orig", ""), "succeeded").prepare(context).operand
        operand = replace(operand, seconds=seconds)
        recognized = operand.syntax()
        # The admitted native rule supplies the mathematical head; visual adjacency never
        # turns an arbitrary identifier into a function declaration.
        if context.allow_local_definitions:
            for symbol, extent in _heads(recognized):
                definitions.append(dict(symbol=symbol, role="function", authority="source",
                    evidence=f"{pointer}:{extent[0]}:{extent[1]}",
                    source_id=context.source_id,scope=scope,start=ordinal+1,end=end))
        result = operand.symbolic_reading()
        out.append(NativeReading(pointer, operand, result, start, context_issues))
    batch.native[key] = tuple(out)
    return tuple(out)


def native_result(unit: Any, cfg: Any, ctx: Any, method: str) -> UnitResult:
    from corpus_structure.core.payloads import ValuePayload
    from .spans import SpanReading, MathSpan, formula_values
    from corpus_structure.core.evidence import Segment
    from corpus_structure.core.vocab import SegmentKind

    view = ctx.reader.source_view(unit.ref.unit_id)
    selected = readings(view, cfg, ctx.reader)
    drafts: list[ObservationDraft[Any]] = []
    for reading in selected:
        text = reading.prepared.latex
        projected = None if reading.projected_start is None else (
            reading.projected_start, reading.projected_start + len(text))
        if method == "normalize.formula":
            segment = Segment(kind=SegmentKind.MATH_DISPLAY, start=0, end=len(text))
            value = formula_values([SpanReading(MathSpan(segment, text, 0), reading.result,
                                               reading.prepared)])[0]
            fields: dict[str,Any] = {"value": value.value}
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
                    recognized_start=symbol.start, recognized_end=symbol.end,
                    context_basis=tuple(vars(d) for d in reading.prepared.context.declarations if d.authority=="source"),
                    context_issues=reading.context_issues)
                location = None if reading.projected_start is None else (
                    reading.projected_start + symbol.start, reading.projected_start + symbol.end)
                drafts.append(ObservationDraft(kind=ObservationKind.MENTION, payload=payload,
                    payload_class=NativeSymbolPayload, payload_version="3", source_view_id=view.ref.id,
                    native_pointer=reading.pointer, projected_span=location,
                    recognized_span=(symbol.start, symbol.end)))
            if reading.result.tree is not None:
                from .spans import _relations
                for relation in _relations(reading.result.tree, MathSpan(
                    Segment(kind=SegmentKind.MATH_DISPLAY,start=0,end=len(text)),text,0)):
                    payload = NativeRelationPayload(label=relation.label,source_pointer=reading.pointer,
                        recognized_head=relation.head,recognized_tail=relation.tail)
                    drafts.append(ObservationDraft(kind=ObservationKind.RELATION,payload=payload,
                        payload_class=NativeRelationPayload,payload_version="3",source_view_id=view.ref.id,
                        native_pointer=reading.pointer,projected_span=projected,recognized_span=(0,len(text))))
    import dataclasses
    import sympy
    from .transform import NotRepresentable
    analysis_items=[]
    source_items={item["self_ref"]:item for item in view.items}
    for reading in selected:
        operand=reading.prepared
        record=dict(pointer=reading.pointer,orig=source_items[reading.pointer].get("orig",""),
            recognized_latex=operand.latex,recognition_health="succeeded",
            context_basis=operand.context.stage_key("symbolic"),
            context=dict(source_id=operand.context.source_id,scope=operand.context.scope,
                declarations=[dataclasses.asdict(d) for d in operand.context.declarations],
                issues=reading.context_issues),**_syntax_value(reading.result))
        try:
            record["symbolic"]=dict(format="sympy-srepr-1",expression=sympy.srepr(operand.symbolic_value()))
        except (NotRepresentable,grammar.NotParsed,grammar.Ambiguous) as error:
            record["symbolic"]=dict(outcome="unsupported",diagnostic=str(error))
        record["definedness"]=dataclasses.asdict(operand.definedness_result())
        record["stages"]={name:dataclasses.asdict(operand.state(name)) for name in
            ("lexical","syntax","interpretation","occurrences","symbolic","scientific")}
        analysis_items.append(record)
    if analysis_items:
        analysis=NativeAnalysisPayload(source_view_id=view.ref.id,
            native_product=view.ref.native_product.values(),projection_digest=view.ref.projection_digest,
            recipe_digest=view.ref.recipe_digest,demand="symbolic",items=tuple(analysis_items))
        drafts.append(ObservationDraft(kind=ObservationKind.RECORD,payload=analysis,
            payload_class=NativeAnalysisPayload,payload_version="1",source_view_id=view.ref.id))
    recognized = {r.pointer for r in selected}
    formulas = {i["self_ref"] for i in view.items if i.get("label") == "formula"}
    complete = formulas <= recognized and all(r.result.status == ParseOutcome.OK and not r.context_issues for r in selected)
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


def _tree_value(node):
    from lark import Tree,Token
    if isinstance(node, Token):
        return dict(token=node.type, text=str(node), start=node.start_pos, end=node.end_pos)
    if isinstance(node, Tree):
        from ._tree import span
        extent = span(node)
        return dict(rule=node.data, extent=extent,
                    children=[_tree_value(child) for child in node.children])
    raise TypeError("unsupported positioned syntax node")

def _syntax_value(result):
    import dataclasses
    return dict(outcome=result.status.value, kind=result.kind, tail=result.tail,
        failure=None if result.failure is None else dataclasses.asdict(result.failure),
        syntax=None if result.tree is None else _tree_value(result.tree),
        occurrences=[dataclasses.asdict(o) for o in result.occurrences],
        declarations=[dataclasses.asdict(d) for d in result.declarations], notes=list(result.notes))


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
                            seconds: float = grammar.PARSE_SECONDS,
                            domain_rules: tuple[NativeDomainRule,...] = (),
                            ancestor_declarations: tuple[dict[str,Any],...] = (),
                            ancestor_context_issues: tuple[str,...] = ()) -> NativeAnalysisPayload:
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

    definitions = list(ancestor_declarations)
    results = []
    positions={item["self_ref"]:n for n,item in enumerate(view.items)}
    for item in formulas:
        ref = item["self_ref"]
        outcome = health.get(ref, "unknown")
        selected = pointer is None or ref == pointer
        if outcome != "succeeded":
            if selected:
                results.append(dict(pointer=ref, orig=item.get("orig", ""), recognized_latex=item["text"],
                                    recognition_health=outcome, availability="unavailable"))
            continue
        ordinal=positions[ref]
        source_id,scope,end=_declaration_scope(view,domain_rules,ordinal)
        context = prepare_interpretation_context(prepared, macros={},
            source_id=source_id,scope=scope,offset=ordinal,
            scope_chain=(f"{source_id}:section:{view.ref.section_pointer}",),
            declarations=definitions, demand=demand)
        operand = PreparedMathInput(context, item["text"], seconds=seconds)
        # Only contextual demands need prior mathematical declaration recognition.
        contextual = demand in {"interpretation", "occurrences", "symbolic", "scientific"}
        if contextual and context.allow_local_definitions and "(" in item["text"].partition("=")[0] and "=" in item["text"]:
            for symbol, extent in _heads(operand.syntax()):
                definitions.append(dict(symbol=symbol, role="function", authority="source",
                    evidence=f"{ref}:{extent[0]}:{extent[1]}", source_id=context.source_id,
                    scope=scope,start=ordinal+1,end=end))
        if not selected:
            continue
        value = dict(pointer=ref, orig=item.get("orig", ""), recognized_latex=item["text"],
            recognition_health=outcome, availability="available", context_basis=context.stage_key(
                demand, **({"conditions": [dataclasses.asdict(c) for c in operand.definedness()],
                           "precision": {"mode": "exact-symbolic"}, "sampling": {"requested": False},
                           "decision_policy": {"question": question, "predicate": predicate}}
                          if demand == "scientific" else {})))
        value["context"] = dict(source_id=context.source_id,scope=context.scope,
            declarations=[dataclasses.asdict(d) for d in context.declarations],
            coverage="complete" if domain_rules and not ancestor_context_issues else "unknown",
            issues=ancestor_context_issues)
        if demand == "lexical":
            value["lexical"] = [dict(kind=t.kind, text=t.text, start=t.start, end=t.end)
                                for t in operand.lexical()]
        elif demand == "structure":
            capture = operand.structure()
            value["structure"] = dict(outcome=capture.structure_outcome,
                nodes=[dataclasses.asdict(n) for n in capture.nodes], issues=capture.issues)
        elif demand == "syntax":
            value.update(_syntax_value(operand.syntax()))
        else:
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
    extents = split([block], SentenceConfig(), layouts=[view.layout],
                    policy=getattr(view,"text_policy",None))[0]
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
    parent_views,_=ancestor_views(reader,view)
    parent_index={parent.ref.id:parent for parent in parent_views}
    context_sources={}
    for record in observations:
        value=record.get("payload",{})
        if not isinstance(value,Mapping):
            continue
        source_id=value.get("binding_source_view_id")
        pointer=value.get("binding_pointer")
        parent=parent_index.get(source_id)
        if parent is not None and pointer is not None:
            item=next((i for i in parent.items if i["self_ref"]==pointer),None)
            if item is not None:
                context_sources[source_id,pointer]=dict(kind="ancestor_source",
                    source_view_id=source_id,native_product=parent.ref.native_product.values(),
                    projection_digest=parent.ref.projection_digest,item=item,
                    binding_quote=value.get("binding_quote"))
    observations.extend(context_sources.values())
    known_classes = {entity.entity_id: tuple(getattr(entity, "classes", ())) for entity in known}
    return proposal_packet(prepared, frame, guideline=reader.guideline(),
        configuration=configuration, known_classes=known_classes,
        known_entities=tuple(KnownProposalEntity(entity.entity_id, entity.label, entity.aliases)
                             for entity in known),
        macros={}, native_observations=tuple(observations))


class NativeContextDeclaration(BaseModel):
    model_config=ConfigDict(frozen=True,extra="forbid")
    symbol:str
    role:Literal["variable","function"]
    rule_id:str
    source_pointer:str
    recognized_start:int
    recognized_end:int
    scope_pointer:str
    quote:str
    projection_start:int|None=None
    projection_end:int|None=None


class NativeContextPayload(BaseModel):
    model_config=ConfigDict(frozen=True,extra="forbid")
    source_view_id:int
    native_product:dict[str,Any]
    projection_digest:str
    demand:Literal["context_declarations"]="context_declarations"
    declarations:tuple[NativeContextDeclaration,...]
    issues:tuple[str,...]=()


def native_context_result(unit:Any,view:Any,cfg:Any,reader:Any)->UnitResult:
    """Prepare demanded ancestor roles without all-parent M09/M11 or native algebra."""
    from corpus_structure.core.evidence import Segment
    from corpus_structure.core.vocab import SegmentKind
    from corpus_structure.ingest.sentences import Block,SentenceConfig,split
    from .prepared import PreparedMathInput
    from .scope import math_tokens
    from .spans import MathSpan,SpanReading,extract,formula_values
    import re

    section=cfg.section()
    pieces={p["item_ref"]:p for p in view.pieces if p.get("item_ref")}
    native={i["self_ref"]:i for i in view.items}
    mathematical=tuple((p["start"],p["end"]) for p in view.pieces
        if p.get("item_ref") in native and native[p["item_ref"]].get("label")=="formula")
    sentences=split([Block(view.text,mathematical,(),())],cfg.sentences,layouts=[view.layout],
                    policy=getattr(view,"text_policy",None))[0]
    health={o["pointer"]:o["outcome"] for o in view.health.get("formula_outcomes",())}
    declarations=[];issues=[]
    for ordinal,item in enumerate(view.items):
        if item.get("label")!="formula":continue
        pointer=item["self_ref"];latex=item["text"];piece=pieces.get(pointer)
        function_candidate="(" in latex.partition("=")[0] and "=" in latex
        sentence=None
        prefix=""
        if piece is not None:
            sentence=next(((a,b) for a,b in sentences if a<=piece["start"]<b),None)
            if sentence is not None:prefix=view.text[sentence[0]:piece["start"]].strip().casefold()
        initial=any(re.match(re.escape(word.casefold())+r"\b",prefix)
                    for word in cfg.binders.sentence_initial)
        clause=any(re.search(r"\b"+re.escape(word.casefold())+r"\b",prefix)
                   for word in cfg.binders.clause)
        wide=any(re.search(r"\b"+re.escape(word.casefold())+r"\b",prefix)
                 for word in cfg.binders.section_wide)
        if not function_candidate and not(initial or clause or wide):continue
        if health.get(pointer)!="succeeded":
            issues.append("ancestor declaration recognition unavailable: "+pointer);continue
        _,scope,_=_declaration_scope(view,section.native_domain_rules,ordinal)
        if ":section:" not in scope and not wide:continue
        context=prepare_interpretation_context(getattr(reader,"prepared",None),macros={},constants=section.constants)
        operand=PreparedMathInput(context,latex)
        syntax=operand.syntax()
        if syntax.tree is None:
            issues.append("ancestor declaration syntax unavailable: "+pointer);continue
        quote=latex if sentence is None else view.text[sentence[0]:sentence[1]]
        if function_candidate:
            for symbol,(a,b) in _heads(syntax):
                declarations.append(NativeContextDeclaration(symbol=symbol,role="function",
                    rule_id="function-definition-1",source_pointer=pointer,recognized_start=a,recognized_end=b,
                    scope_pointer=view.ref.section_pointer,quote=quote,
                    projection_start=None if sentence is None else sentence[0],projection_end=None if sentence is None else sentence[1]))
        if initial or clause or wide:
            reading=operand.interpretation()
            segment=Segment(kind=SegmentKind.MATH_INLINE,start=0,end=len(latex))
            rows=[SpanReading(MathSpan(segment,latex,0),reading,operand)]
            found=extract(rows)
            token=math_tokens(formula_values(rows),found.mentions,found.relations).get(0)
            if token is not None:
                for mention in token.bound:
                    declarations.append(NativeContextDeclaration(symbol=mention.name,role="variable",
                        rule_id="binder:section_wide" if wide else "binder:initial" if initial else "binder:clause",
                        source_pointer=pointer,recognized_start=mention.start,recognized_end=mention.end,
                        scope_pointer=view.ref.section_pointer,quote=quote,
                        projection_start=None if sentence is None else sentence[0],projection_end=None if sentence is None else sentence[1]))
    payload=NativeContextPayload(source_view_id=view.ref.id,native_product=view.ref.native_product.values(),
        projection_digest=view.ref.projection_digest,declarations=tuple(declarations),issues=tuple(issues))
    draft=ObservationDraft(kind=ObservationKind.RECORD,payload=payload,payload_class=NativeContextPayload,
        payload_version="1",source_view_id=view.ref.id)
    return UnitResult(ref=unit.ref,outcome=ObservationOutcome.PRODUCED,observations=(draft,),
        coverage=(CoverageDraft(family="resolve.symbol_scope",scope=view.ref.key,
            outcome="partial" if issues or not section.native_domain_rules else "complete",
            reason="ancestor declaration preparation incomplete" if issues or not section.native_domain_rules else None,
            required_capability="context_declarations"),))


def _inherited_bindings(reader: Any, view: Any):
    parents,missing=ancestor_views(reader,view)
    issues=list(missing)
    result={}
    for parent in sorted(parents,key=lambda v:len(v.ancestors),reverse=True):
        rows=reader.source_observations(parent.ref.id,"resolve.symbol_scope",ObservationKind.SCOPE)
        coverage=reader.source_view_coverage(parent.ref.id,"resolve.symbol_scope")
        if not coverage or any(row.coverage.outcome!="complete" for row in coverage):
            issues.append("ancestor symbol-scope coverage incomplete: "+parent.ref.key)
        native_order={item["self_ref"]:n for n,item in enumerate(parent.items)}
        candidates={}
        for row in rows:
            value=row.payload
            if value.get("outcome")!="resolved" or value.get("scope_pointer")!=parent.ref.section_pointer:
                continue
            pointer=value.get("binding_pointer")
            if pointer is None or _before_descendant(parent,view,pointer) is not True:
                continue
            position=(native_order.get(pointer,-1),value.get("scope_start") or 0)
            symbol=value["symbol"]
            if symbol not in candidates or position>candidates[symbol][0]:
                candidates[symbol]=(position,parent,value)
        for row in reader.source_observations(parent.ref.id,"resolve.symbol_scope",ObservationKind.RECORD):
            value=row.payload
            if value.get("demand")!="context_declarations":continue
            for declaration in value.get("declarations",()):
                if declaration.get("role")!="variable" or declaration.get("scope_pointer")!=parent.ref.section_pointer:
                    continue
                pointer=declaration["source_pointer"]
                if _before_descendant(parent,view,pointer) is not True:continue
                position=(native_order.get(pointer,-1),declaration["recognized_start"])
                symbol=declaration["symbol"]
                basis=dict(binding_observation=row.observation_key,binding_pointer=pointer,
                    binding_source_view_id=parent.ref.id,binding_projection_digest=parent.ref.projection_digest,
                    binding_quote=declaration["quote"],scope_pointer=parent.ref.section_pointer,
                    scope_start=declaration.get("projection_start"),scope_end=len(parent.text),
                    input_role="native_parent_context")
                if symbol not in candidates or position>candidates[symbol][0]:
                    candidates[symbol]=(position,parent,basis)
        for symbol,(_,owner,value) in candidates.items():
            result.setdefault(symbol,(owner,value))
    return result,tuple(issues)


def native_scope_result(unit: Any, cfg: Any, ctx: Any) -> UnitResult:
    """Reuse positioned scope kernels on an in-memory lowering of one native section."""
    from dataclasses import replace
    from hashlib import sha256
    from corpus_structure.core.evidence import RenditionContent, Segment
    from corpus_structure.core.method import SourceObservationReference
    from corpus_structure.core.vocab import SegmentKind
    from corpus_structure.ingest.sentences import Block, SentenceConfig, TextLayout, split
    from .scope import resolve_scopes
    from .spans import MathRelation, SpanValue, SymbolMention
    from corpus_structure.core.payloads import ValuePayload
    from corpus_structure.core.values import Formula, SetValue
    from corpus_structure.core.vocab import MathKind
    from .methods import _KIND_OF
    from types import SimpleNamespace

    view = ctx.reader.source_view(unit.ref.unit_id)
    if getattr(unit,"context_only",False) or not getattr(view.ref,"analysis_eligible",True):
        return native_context_result(unit,view,cfg,ctx.reader)
    cfgsentences = cfg.sentences
    if not isinstance(cfgsentences, SentenceConfig) or cfg.binders is None:
        raise ValueError("native symbol scope requires resolved sentence and binder configuration")
    section = cfg.section()
    domains = domain_blocks(view, section.native_domain_rules)
    native = {item["self_ref"]:item for item in view.items if item.get("label")=="formula"}
    pieces_by_ref = {p["item_ref"]:p for p in view.pieces if p.get("item_ref")}
    selected = {pointer:SimpleNamespace(prepared=SimpleNamespace(latex=item["text"]),
        projected_start=pieces_by_ref[pointer]["start"] if pointer in pieces_by_ref and
            view.text[pieces_by_ref[pointer]["start"]:pieces_by_ref[pointer]["end"]]==item["text"] else None)
        for pointer,item in native.items()}
    blocks, pieces, math_segments, layouts = [], [], {}, {}
    for pointer,reading in selected.items():
        start=reading.projected_start
        if start is not None:
            math_segments[pointer]=Segment(kind=SegmentKind.MATH_INLINE,start=start,
                end=start+len(reading.prepared.latex),attrs={"native_pointer":pointer})
    # Native text/formula items may be fragments of the same mathematical sentence.
    # Partition only on attributed statement scopes, not on every PDF item/page boundary.
    cuts=sorted({0,len(view.text),*(start for start,_,_,_ in domains)})
    for a,b in zip(cuts,cuts[1:]):
        if a==b:
            continue
        mathematical=tuple((node.start-a,node.end-a) for node in math_segments.values()
                           if a<=node.start and node.end<=b)
        blocks.append(Block(view.text[a:b],mathematical,(),()))
        pieces.append(dict(start=a,end=b))
        base=view.layout
        layouts[a,b]=replace(base,block_start=a,block_end=b,
            text_digest=sha256(view.text[a:b].encode()).hexdigest(),
            tokens=tuple(token for token in base.tokens if a<=token.start and token.end<=b),display=())
    extents=split(blocks,cfgsentences,layouts=[layouts[p["start"],p["end"]] for p in pieces],
                  policy=getattr(view,"text_policy",None))
    paragraphs=[]
    for piece,sentences in zip(pieces,extents,strict=True):
        a,b=piece["start"],piece["end"]
        children=[Segment(kind=SegmentKind.SENTENCE,start=a+x,end=a+y) for x,y in sentences]
        children.extend(node for node in math_segments.values() if a<=node.start and node.end<=b)
        paragraphs.append(Segment(kind=SegmentKind.PARAGRAPH,start=a,end=b,
                                  children=tuple(children)))
    root_children=[]
    used=set()
    for start,end,pointer,rule in domains:
        children=tuple(paragraph for paragraph in paragraphs if start<=paragraph.start and paragraph.end<=end)
        used.update(id(p) for p in children)
        root_children.append(Segment(kind=SegmentKind.UNIT,start=start,end=end,
            attrs={"native_pointer":pointer,"recognition_rule":rule.rule_id},children=children))
    root_children.extend(p for p in paragraphs if id(p) not in used)
    content=RenditionContent(canonical_text=view.text,
        document=Segment(kind=SegmentKind.DOCUMENT,start=0,end=len(view.text),
                         attrs={"native_pointer":view.ref.section_pointer},children=tuple(root_children)))
    # This value is solely a pure-kernel lowering: it is never stored as kb.rendition.
    stored=ctx.reader.source_observations(view.ref.id,"extract.math",ObservationKind.MENTION)
    values=[]
    for row in ctx.reader.source_observations(view.ref.id,"normalize.formula",ObservationKind.VALUE):
        pointer = getattr(row,"native_pointer",None)
        if pointer is None:
            continue
        if pointer in math_segments:
            value=ValuePayload.model_validate(row.payload)
            if not isinstance(value.value,Formula|SetValue):
                raise ValueError("native mathematical value report has a nonmathematical value")
            values.append(SpanValue(math_segments[pointer],value.value,
                _KIND_OF.get(value.math_kind) if isinstance(value.math_kind,MathKind) else None,
                value.parse_error if isinstance(value.parse_error,str) else None))
    mentions=[]
    for row in stored:
        payload=row.payload
        pointer=payload["source_pointer"]
        if pointer not in math_segments:
            continue
        offset=selected[pointer].projected_start
        info=payload["math"]
        mentions.append(SymbolMention(math_segments[pointer],offset+payload["recognized_start"],
            offset+payload["recognized_end"],info["name"],info["base"],info.get("sub"),info.get("sup"),
            info.get("constant",False),info.get("in_subscript_of")))
    relations=[]
    for row in ctx.reader.source_observations(view.ref.id,"extract.math",ObservationKind.RELATION):
        payload=row.payload
        pointer=payload["source_pointer"]
        if pointer in math_segments:
            offset=selected[pointer].projected_start
            relations.append(MathRelation(math_segments[pointer],payload["label"],
                tuple(offset+x for x in payload["recognized_head"]),
                tuple(offset+x for x in payload["recognized_tail"]),""))
    scopes=resolve_scopes(content,values,mentions,relations,{},cfg.binders,cfgsentences,
                          text_layouts=layouts,text_policy=getattr(view,"text_policy",None))
    locations={}
    for row in stored:
        payload=row.payload
        locations[(payload.get("source_pointer"),payload.get("recognized_start"),payload.get("recognized_end"))]=row
    pointers={id(segment):pointer for pointer,segment in math_segments.items()}
    by_position={(pointer,mention.start-selected[pointer].projected_start,
                  mention.end-selected[pointer].projected_start):scope
                 for scope in scopes for mention in (scope.mention,)
                 if (pointer:=pointers.get(id(mention.segment))) is not None}
    inherited,ancestor_issues=_inherited_bindings(ctx.reader,view)
    drafts: list[ObservationDraft[Any]]=[]
    for row in stored:
        raw=row.payload
        if raw["math"].get("constant"):
            continue
        pointer=raw["source_pointer"]
        start,end=raw["recognized_start"],raw["recognized_end"]
        scope=by_position.get((pointer,start,end))
        site=None if scope is None else scope.site
        binding=None
        if site is not None:
            bp=pointers[id(site.mention.segment)]
            offset=selected[bp].projected_start
            binding=locations.get((bp,site.mention.start-offset,site.mention.end-offset))
        parent_binding=inherited.get(raw["math"]["name"]) if site is None else None
        payload=NativeScopePayload(source_pointer=pointer,recognized_start=start,recognized_end=end,
            symbol=raw["math"]["name"],outcome="resolved" if site is not None and binding is not None else "unresolved",
            binding_observation=None if binding is None else binding.observation_key,
            binding_pointer=None if site is None else pointers[id(site.mention.segment)],
            binding_source_view_id=view.ref.id if binding is not None else None,
            binding_projection_digest=view.ref.projection_digest if binding is not None else None,
            binding_quote=None if site is None else view.text[site.sentence.start:site.sentence.end],
            scope_source_view_id=view.ref.id if site is not None else None,
            scope_projection_digest=view.ref.projection_digest if site is not None else None,
            extent=None if site is None else "section" if site.scope.kind is SegmentKind.DOCUMENT else str(site.extent),
            scope_pointer=(site.scope.attrs.get("native_pointer") if site is not None
                and isinstance(site.scope.attrs.get("native_pointer"),str) else None),
            scope_start=None if site is None else site.start,scope_end=None if site is None else site.end,
            reason=None if site is not None and binding is not None else "native binding unavailable or unresolved")
        refs=[SourceObservationReference(row.observation_key,"mention")]
        if parent_binding is not None:
            owner,basis=parent_binding
            payload=payload.model_copy(update=dict(outcome="resolved",reason=None,
                binding_observation=basis["binding_observation"],binding_pointer=basis["binding_pointer"],
                binding_source_view_id=basis.get("binding_source_view_id",owner.ref.id),
                binding_projection_digest=basis.get("binding_projection_digest",owner.ref.projection_digest),
                binding_quote=basis.get("binding_quote"),scope_pointer=basis["scope_pointer"],
                scope_source_view_id=owner.ref.id,scope_projection_digest=owner.ref.projection_digest,
                scope_start=basis.get("scope_start"),scope_end=basis.get("scope_end"),extent="section"))
            refs.append(SourceObservationReference(basis["binding_observation"],basis.get("input_role","binding_site")))
        if binding is not None:
            refs.append(SourceObservationReference(binding.observation_key,"binding_site"))
        offset=selected[pointer].projected_start if pointer in selected else None
        drafts.append(ObservationDraft(kind=ObservationKind.SCOPE,payload=payload,
            payload_class=NativeScopePayload,payload_version="3",source_view_id=view.ref.id,
            native_pointer=pointer,recognized_span=(start,end),
            projected_span=None if offset is None else (offset+start,offset+end),input_refs=tuple(refs)))
    for start,end,pointer,rule in domains:
        payload=NativeDomainPayload(rule_id=rule.rule_id,pattern=rule.pattern,
            statement_kind=rule.statement_kind,scope_role=rule.scope_role,
            source_pointer=pointer,start=start,end=end)
        drafts.append(ObservationDraft(kind=ObservationKind.AUTHOR_MARKUP,payload=payload,
            payload_class=NativeDomainPayload,payload_version="3",source_view_id=view.ref.id,
            native_pointer=pointer,projected_span=(start,end)))
    incomplete=any(d.kind is ObservationKind.SCOPE and d.payload.outcome=="unresolved" for d in drafts)
    upstream=ctx.reader.source_view_coverage(view.ref.id,"extract.math")
    incomplete=incomplete or bool(ancestor_issues) or not section.native_domain_rules or not upstream or any(r.coverage.outcome!="complete" for r in upstream)
    return UnitResult(ref=unit.ref,outcome=ObservationOutcome.PRODUCED if drafts else ObservationOutcome.EMPTY,
        observations=tuple(drafts),coverage=(CoverageDraft(family="resolve.symbol_scope",scope=view.ref.key,
            outcome="partial" if incomplete else "complete",
            reason="native source scope or upstream recognition is incomplete" if incomplete else None,
            required_capability="interpretation"),))
