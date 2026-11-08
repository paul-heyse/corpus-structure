"""Publish neutral linguistic evidence and separate interpretations on the same source."""

import re
from bisect import bisect_right
from collections import defaultdict
from dataclasses import dataclass
from typing import Any

from corpus_structure.ingest.annotations import AnnotationProduct
from corpus_structure.semantic.contributions import (
    contribution_identity,
    occurrence_identity,
    operation_identity,
)
from corpus_structure.semantic.identity import canonical_bytes
from corpus_structure.semantic.observations import source_value
from corpus_structure.semantic.source_contexts import ContextRefused, evidence_anchor
from corpus_structure.semantic.structural_parsing import parse_threshold

from .predicate_frames import interpretation_recipe, source_layout


@dataclass(frozen=True)
class Passage:
    key: str
    start: int
    end: int
    version: str | None = None


def predicate_results(frame, annotations, source_pieces, items):
    from .structural_roles import predicate_frames

    return tuple(
        (
            annotation,
            predicate_frames(
                frame.text,
                (annotation,),
                layout=source_layout(annotation, frame.text, source_pieces, items),
            ),
        )
        for annotation in annotations
        if isinstance(annotation, AnnotationProduct)
    )


def _numeric_condition(cue_variant, text, recipe):
    marker, _, expression = text.strip(" \t\r\n").partition(" ")
    if marker.lower() != cue_variant or cue_variant not in recipe["condition_markers"]:
        return None
    number = recipe["number_pattern"]
    match = re.fullmatch(
        rf"[ \t\r\n]*({number})[ \t]+(>=|<=|>|<|=|≥|≤)[ \t\r\n]*({number})[ \t\r\n]*",
        expression,
    )
    if match is None:
        return None
    left, operator, right = match.groups()
    parsed = parse_threshold(f"{operator} {right}")
    if parsed is None:
        return None
    comparison = dict(
        kind="compare",
        relation=recipe["comparators"][operator],
        lhs=dict(kind="expression", language="text", expression=left, form="formula"),
        rhs=dict(kind="expression", language="text", expression=parsed["value"], form="formula"),
    )
    return dict(kind="not", term=comparison) if cue_variant == "unless" else comparison


def _condition(kind, cue_variant, text, *, contiguous, version="3"):
    if kind not in {"condition", "assumption"}:
        return None
    if version in {"4", "5"}:
        recipe = interpretation_recipe()
        formal = _numeric_condition(cue_variant, text, recipe) if contiguous else None
        return formal or dict(kind="escape", text=text, reason=recipe["escape_reason"])
    # Formal lowering needs operands that carry their own meaning. A bare symbol
    # or unit needs a separate source binding. The located text remains usable.
    marker, _, expression = text.strip().partition(" ")
    if contiguous and cue_variant in {"if", "when", "unless"} and marker.lower() == cue_variant:
        left, separator, right = expression.strip().partition(" ")
        parsed = parse_threshold(right) if separator and left else None
        if (
            parsed is not None
            and parsed["quantity"] is None
            and parsed["unit"] is None
            and parse_threshold("= " + left) is not None
        ):

            def number(value):
                return dict(kind="expression", language="text", expression=value, form="formula")

            comparison = dict(
                kind="compare",
                relation=parsed["comparator"],
                lhs=number(left),
                rhs=number(parsed["value"]),
            )
            return dict(kind="not", term=comparison) if marker.lower() == "unless" else comparison
    return dict(
        kind="escape",
        text=text,
        reason="Located qualifier retained without a supported formal interpretation.",
    )


def publish_predicate_evidence(
    frame,
    context,
    pin,
    dependency,
    results,
    annotation_errors,
    annotation_origin_task_id,
    passages,
    products,
    coordinates,
    *,
    version="2",
):
    """Bind each role to exact native pieces before constructing frame/attachment identities."""
    import json

    from .predicate_cross_block import CrossBlockTarget, cross_block_qualifiers

    if version not in {"2", "3", "4", "5"}:
        raise ValueError("unknown predicate contribution recipe")
    native = json.loads(frame.native_context)
    pieces = tuple(piece for piece in native["pieces"] if piece["kind"] == "native_text")
    piece_ends = tuple(piece["end"] for piece in pieces)
    scope = (
        None
        if passages is None
        else tuple(Passage(p.passage_id, p.start, p.end, p.effective_version) for p in passages)
    )
    questions = ("source_predicate_frames", "source_predicate_interpretation")
    versions = (version, version)
    operations = tuple(
        operation_identity(
            question,
            version,
            pin,
            None if scope is None else tuple((p.key, p.start, p.end, p.version) for p in scope),
        )
        for question, version in zip(questions, versions, strict=True)
    )
    emitted = {operation: 0 for operation in operations}
    retained = tuple("annotation:" + annotation.dependency_digest for annotation, _ in results)
    issues = [*annotation_errors, *(str(issue) for _, result in results for issue in result.issues)]
    unavailable = any(not result.frames and result.issues for _, result in results)
    mapped_cache = {}
    row_cache = {}

    def emit(
        index,
        key,
        semantic_type,
        deps,
        *,
        kind,
        anchors=(),
        members=(),
        component=None,
        endpoints=(),
        value=None,
    ):
        op = operations[index]
        row = dict(
            contract="RetainedContributionSemantics",
            kind=kind,
            semantic_type="structural." + semantic_type,
            operation_key=op,
            item_key=key,
            pin=pin,
            anchors=anchors,
            disposition="located_proposal" if kind == "occurrence" else "scoped_proposal",
            standing="retained_private",
            score_state="missing",
            computation_dependencies=deps,
        )
        if anchors:
            row["occurrence_id"] = occurrence_identity(anchors)
        if members:
            row["members"] = members
        if endpoints:
            row["endpoints"] = tuple(
                dict(role=role, contribution_id=identity) for role, identity in endpoints
            )
        if component is not None:
            row["component"] = component
        if value is not None:
            row["value"] = source_value(value)
        key = contribution_identity(row)
        if key not in row_cache:
            row["contribution_id"] = key
            row_cache[key] = row
            products.append(row)
            emitted[op] += 1
        return key

    def evidence(annotation, selected, span):
        key = (annotation.dependency_digest, selected, span.tokens, span.extents)
        if key in mapped_cache:
            return mapped_cache[key]
        extents = []
        anchors = []

        def add(lo, hi):
            try:
                mapped = context.map_span(lo, hi, literal=frame.text[lo:hi], allow_multiple=True)
                rows = [evidence_anchor(context, part, native=True) for part in mapped]
            except ContextRefused:
                return False
            for anchor, coordinate in rows:
                coordinates[
                    canonical_bytes({k: v for k, v in coordinate.items() if k != "text"})
                ] = coordinate
                anchors.append(anchor)
            if extents and extents[-1][1] == lo:
                extents[-1] = (extents[-1][0], hi)
            else:
                extents.append((lo, hi))
            return True

        for start, end in span.extents:
            if selected.start <= start < end <= selected.end and add(start, end):
                continue
            first = bisect_right(piece_ends, max(start, selected.start))
            for position in range(first, len(pieces)):
                piece = pieces[position]
                if piece["start"] >= min(end, selected.end):
                    break
                lo = max(start, selected.start, piece["start"])
                hi = min(end, selected.end, piece["end"])
                if lo >= hi:
                    continue
                # Drop boundary fragments of tokens excluded by this passage or
                # by an unsupported coordinate. Preserve the remaining exact runs.
                tokens = [
                    annotation.tokens[i]
                    for i in span.tokens
                    if lo <= annotation.tokens[i].start < annotation.tokens[i].end <= hi
                ]
                if not tokens:
                    continue
                add(tokens[0].start, tokens[-1].end)
        indices = tuple(
            i
            for i in span.tokens
            if any(
                lo <= annotation.tokens[i].start < annotation.tokens[i].end <= hi
                for lo, hi in extents
            )
        )
        mapped_cache[key] = (tuple(extents), tuple(anchors), indices)
        return mapped_cache[key]

    def component(
        index, kind, selected, deps, basis, state="unassessed", *, anchor_ids=(), **fields
    ):
        return dict(
            protocol="witnessed-component-1",
            kind=kind,
            question=questions[index],
            question_version=versions[index],
            scope=selected.key,
            **({"effective_version": selected.version} if selected.version is not None else {}),
            interpretation=state,
            dependencies=deps,
            bases=(
                dict(
                    kind="matched_cue",
                    dependencies=basis,
                    **({"anchor_ids": anchor_ids} if anchor_ids else {}),
                ),
            ),
            **fields,
        )

    def scope_for(annotation):
        if scope is not None:
            return scope
        return (Passage(annotation.block_id, annotation.block_start, annotation.block_end),)

    def cue_row(annotation, selected, cue, dep, bases, *, cross_hosts=()):
        kind = {"temporal": "order", "polarity": "negation"}.get(cue.kind, cue.kind)
        if kind not in {
            "condition",
            "assumption",
            "parameterization",
            "population_inclusion",
            "exception",
            "attribution",
            "modality",
            "negation",
            "order",
            "dependency",
            "contrast",
            "example",
            "quotation",
        }:
            return None
        extents, anchors, tokens = evidence(annotation, selected, cue.span)
        if not anchors:
            return None
        basis_extents, basis_anchors, basis_tokens = evidence(annotation, selected, cue.basis)
        whole = extents == cue.span.extents and basis_extents == cue.basis.extents
        host_state = (
            "located"
            if whole and cue.status == "located" and (cue.hosts or cross_hosts)
            else "unresolved"
        )
        cross_hosts = cross_hosts if host_state == "located" else ()
        source_text = " ".join(frame.text[a:b] for a, b in extents)
        marker = (
            emit(
                0,
                f"{selected.key}:{dep}:marker:{basis_tokens}",
                "predicate_member",
                bases,
                kind="occurrence",
                anchors=basis_anchors,
                value=dict(role="marker", text=" ".join(frame.text[a:b] for a, b in basis_extents)),
            )
            if basis_anchors
            else None
        )
        dependencies = (*bases, *cross_hosts, *((marker,) if marker is not None else ()))
        key = emit(
            0,
            f"{selected.key}:{dep}:{kind}:{cue.variant}:{tokens}",
            "predicate_cue",
            dependencies,
            kind="occurrence",
            anchors=anchors,
            members=(marker,) if marker is not None else (),
            component=component(
                0,
                "predicate_cue",
                selected,
                dependencies,
                bases,
                annotation=dep,
                block=annotation.block_id,
                cue_kind=kind,
                variant=cue.variant,
                host_state=host_state,
                candidate_tokens=cue.hosts,
                **({"cross_block_hosts": cross_hosts} if cross_hosts else {}),
                token_indices=tokens,
                extents=tuple(dict(start=a, end=b) for a, b in extents),
                marker_extents=tuple(dict(start=a, end=b) for a, b in basis_extents),
                marker_token_indices=basis_tokens,
                **({"marker_member": marker} if marker is not None else {}),
                anchor_ids=tuple(a["anchor_id"] for a in basis_anchors),
                **({"governing_token": cue.origin} if cue.origin is not None else {}),
                **({"subordinate_token": cue.component} if cue.component is not None else {}),
            ),
            value=dict(
                text=source_text,
                extents=tuple(dict(start=a, end=b) for a, b in extents),
                marker_extents=tuple(dict(start=a, end=b) for a, b in basis_extents),
            ),
        )
        return key, kind, host_state, source_text, len(extents) == 1

    def attach(selected, located, variant, target, bases, *, witness=None):
        qualifier, kind, _, source_text, contiguous = located
        host, reading_id = target.frame, target.reading
        lowered = _condition(kind, variant, source_text, contiguous=contiguous, version=version)
        details: dict[str, Any] = {}
        if lowered is not None:
            details["condition"] = source_value(lowered)
            modality = {
                "definition": "defined",
                "assumption_restriction": "supposed",
                "described_process": "asserted",
            }.get(target.interpretation)
            if modality is not None and target.polarity != "unresolved":
                details["interpretation_member"] = reading_id
                details["qualification"] = source_value(
                    dict(
                        modality=modality,
                        polarity=target.polarity == "positive",
                        scope=dict(extent="statement", locator=host),
                        condition=lowered,
                    )
                )
        members = (qualifier, host, reading_id) if "qualification" in details else (qualifier, host)
        predecessor = ()
        if witness is not None:
            details["host_witness"] = witness
            if "parameterization" in witness:
                predecessor = (witness["parameterization"],)
        deps = (*bases, *members, *predecessor)
        emit(
            1,
            f"{qualifier}:{host}",
            "predicate_qualification",
            deps,
            kind="relation",
            members=members,
            endpoints=(("qualifier", qualifier), ("host", host)),
            component=component(
                1,
                "predicate_qualifier",
                selected,
                deps,
                bases,
                qualifier_contribution_id=qualifier,
                host_contribution_id=host,
                qualifier_kind=kind,
                **details,
            ),
        )

    scoped_hosts = defaultdict(list)
    for annotation, result in results:
        if version in {"3", "4", "5"} and result.frames:
            from corpus_structure.ingest.annotation_views import annotation_view

            from .predicate_frames import _frame_vocabulary
            from .predicate_qualifier_recipes import local_qualifier_result

            view = annotation_view(
                annotation,
                frame.text[annotation.block_start : annotation.block_end],
                _frame_vocabulary(),
                required=("DEP", "POS", "SENT_START"),
            )
            result = local_qualifier_result(view, result)
        dep = "annotation:" + annotation.dependency_digest
        bases = (dependency, dep)
        for selected in scope_for(annotation):
            for cue in result.unresolved_cues:
                cue_row(annotation, selected, cue, dep, bases)
            for candidate in result.frames:
                extents, _, indices = evidence(annotation, selected, candidate.predicate)
                if not extents or extents != candidate.predicate.extents:
                    continue
                predicate_token = indices[0]
                role_rows: list[dict[str, Any]] = []
                unlocated_roles = []

                def member(
                    role,
                    span,
                    head=None,
                    inherited=None,
                    state="complete",
                    *,
                    annotation=annotation,
                    selected=selected,
                    role_rows=role_rows,
                    dep=dep,
                    bases=bases,
                ):
                    extents, anchors, tokens = evidence(annotation, selected, span)
                    if not anchors:
                        return
                    role_rows.append(
                        dict(
                            contribution=emit(
                                0,
                                f"{selected.key}:{dep}:{role}:{tokens}",
                                "predicate_member",
                                bases,
                                kind="occurrence",
                                anchors=anchors,
                                value=dict(
                                    role=role,
                                    text=" ".join(frame.text[a:b] for a, b in extents),
                                    start=extents[0][0],
                                    end=extents[-1][1],
                                )
                                if len(extents) == 1
                                else dict(
                                    role=role,
                                    text=" ".join(frame.text[a:b] for a, b in extents),
                                ),
                            ),
                            role=role,
                            token_indices=tokens,
                            extents=tuple(dict(start=a, end=b) for a, b in extents),
                            outcome=state if extents == span.extents else "partial",
                            **({"head_token": head} if head in tokens else {}),
                            **({"inherited_from": inherited} if inherited is not None else {}),
                        )
                    )

                member("predicate", candidate.predicate, predicate_token)
                member("focus", candidate.focus, predicate_token)
                for role in candidate.roles:
                    row_count = len(role_rows)
                    member(
                        role.name,
                        role.span,
                        role.head,
                        role.inherited_from,
                        "unresolved"
                        if role.status == "unresolved"
                        else ("partial" if role.status == "partial" else "complete"),
                    )
                    if version in {"4", "5"} and len(role_rows) == row_count:
                        selected_tokens = any(
                            selected.start <= token.start < token.end <= selected.end
                            for token in (annotation.tokens[index] for index in role.span.tokens)
                        )
                        unlocated_roles.append(
                            dict(
                                role=role.name,
                                head_token=role.head,
                                token_indices=role.span.tokens,
                                reason="unmappable" if selected_tokens else "outside_selection",
                                **(
                                    {"inherited_from": role.inherited_from}
                                    if role.inherited_from is not None
                                    else {}
                                ),
                            )
                        )
                focus = next((row for row in role_rows if row["role"] == "focus"), None)
                focus_state = (
                    "unavailable"
                    if focus is None
                    else "exact"
                    if focus["outcome"] == "complete" and len(focus["extents"]) == 1
                    else "partial"
                )
                members = tuple(role["contribution"] for role in role_rows)
                key = f"{selected.key}:{dep}:{predicate_token}:{candidate.variant}"
                host = emit(
                    0,
                    key,
                    "predicate_frame",
                    (*bases, *members),
                    kind="composite",
                    members=members,
                    component=component(
                        0,
                        "predicate_frame",
                        selected,
                        (*bases, *members),
                        bases,
                        annotation=dep,
                        block=annotation.block_id,
                        predicate_token=predicate_token,
                        variant=candidate.variant,
                        grammatical_reading=candidate.reading,
                        focus_state=focus_state,
                        frame_members=tuple(role_rows),
                        **({"unlocated_roles": tuple(unlocated_roles)} if unlocated_roles else {}),
                    ),
                )
                polarity = (
                    candidate.polarity
                    if candidate.polarity in {"positive", "negative"}
                    else "unresolved"
                )
                interpretation = candidate.interpretation
                state = "unresolved" if interpretation == "unresolved" else "unassessed"
                read_deps = (*bases, host)
                reading_id = emit(
                    1,
                    key,
                    "predicate_reading",
                    read_deps,
                    kind="composite",
                    members=(host,),
                    component=component(
                        1,
                        "predicate_reading",
                        selected,
                        read_deps,
                        bases,
                        state,
                        frame=host,
                        reading=interpretation,
                        voice=candidate.voice,
                        polarity=polarity,
                    ),
                )
                target = CrossBlockTarget(
                    host,
                    reading_id,
                    interpretation,
                    polarity,
                    annotation,
                    predicate_token,
                )
                if version in {"3", "4", "5"} and scope is not None:
                    scoped_hosts[selected].append(target)
                for cue in candidate.cues:
                    located = cue_row(annotation, selected, cue, dep, bases)
                    if located is None:
                        continue
                    _, kind, host_state, _, _ = located
                    if (
                        host_state != "located"
                        or predicate_token not in cue.hosts
                        or kind in {"contrast", "example", "quotation"}
                    ):
                        continue
                    attach(selected, located, cue.variant, target, bases)

    if version in {"3", "4", "5"} and scope is not None:
        for selected in scope:
            for entry in cross_block_qualifiers(
                frame,
                tuple(annotation for annotation, _ in results),
                selected,
                scoped_hosts[selected],
                row_cache,
                native,
                pieces,
            ):
                dep = "annotation:" + entry.source.dependency_digest
                bases = (dependency, dep)
                located = cue_row(
                    entry.source,
                    selected,
                    entry.cue,
                    dep,
                    bases,
                    cross_hosts=tuple(target.frame for target in entry.targets),
                )
                if located is None or located[2] != "located":
                    continue
                for target in entry.targets:
                    target_dep = "annotation:" + target.annotation.dependency_digest
                    attach(
                        selected,
                        located,
                        entry.cue.variant,
                        target,
                        (*bases, target_dep),
                        witness=entry.witness,
                    )

    reason = "; ".join(issues)
    if not reason and not results:
        reason = "No retained linguistic annotation block is available."
    return tuple(
        dict(
            operation_key=op,
            question=question,
            operation_version=version,
            outcome=("limited" if emitted[op] else "unsupported" if unavailable else "failed")
            if issues
            else ("succeeded" if emitted[op] else "empty" if results else "not_run"),
            **({"reason": reason} if reason else {}),
            inspected_count=sum(len(annotation.tokens) for annotation, _ in results),
            emitted_count=emitted[op],
            **(
                {"annotation_origin_task_id": annotation_origin_task_id}
                if annotation_origin_task_id is not None
                else {}
            ),
            computation_dependencies=tuple(dict.fromkeys((dependency, *retained))),
        )
        for op, question, version in zip(operations, questions, versions, strict=True)
    )
