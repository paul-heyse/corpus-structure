"""Publish neutral linguistic evidence and separate interpretations on the same source."""

from bisect import bisect_right
from collections import defaultdict
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from typing import Any

from pydantic import ValidationError

from corpus_structure.ingest.annotations import AnnotationProduct
from corpus_structure.semantic.contributions import (
    contribution_identity,
    occurrence_identity,
    operation_identity,
)
from corpus_structure.semantic.identity import canonical_bytes
from corpus_structure.semantic.observations import source_value
from corpus_structure.semantic.source_contexts import ContextRefused, evidence_anchor
from corpus_structure.semantic.types import PreparedRelease

from .predicate_frames import source_layout

PREDICATE_QUALIFIER_CLASS = "PredicateQualifierComponent"
MISSING_QUALIFIER = "Predicate qualifier declaration is missing from the selected release."
INCOMPATIBLE_QUALIFIER = "Located attachment differs from the released qualifier declaration."
type QualifierPreflight = Callable[[Mapping[str, Any]], str | None]


def predicate_qualifier_refusal(
    prepared: PreparedRelease, qualifier: Mapping[str, Any]
) -> str | None:
    """Check a proposed relation without risking the independently located parts."""
    if PREDICATE_QUALIFIER_CLASS not in prepared.index.definitions:
        return MISSING_QUALIFIER
    try:
        prepared.validate_json(PREDICATE_QUALIFIER_CLASS, canonical_bytes(qualifier))
    except ValidationError:
        return INCOMPATIBLE_QUALIFIER
    return None


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


def _condition(
    kind,
    formal_operator,
    text,
    *,
    contiguous,
    layers=(),
    projection=None,
    extents=(),
    marker_extents=(),
):
    """Lower only already-retained positioned numeric syntax; never parse cue text."""
    if kind not in {"condition", "assumption"}:
        return None, []
    escaped = dict(
        kind="escape",
        text=text,
        reason="Located qualifier retained without a supported formal interpretation.",
    )
    if not contiguous or formal_operator not in {"compare", "not_compare"} or len(extents) != 1:
        return escaped, []
    start, end = extents[0]
    values = {}
    conflicted = False
    for pin, report in layers.items() if hasattr(layers, "items") else ():
        body = report.payload
        occurrences = {o["local_id"]: o for o in body["occurrences"]}
        for annotation in body["annotations"]:
            normalized = annotation.get("formal", {}).get("normalized")
            if (
                not normalized
                or normalized["kind"] not in {"decimal", "comparator"}
                or normalized["domain_status"] not in {"valid", "not_requested"}
            ):
                continue
            spans = [e for oid in annotation["occurrences"] for e in occurrences[oid]["extents"]]
            if len(spans) != 1:
                continue
            span = spans[0]
            if (
                span["projection"] == projection
                and start <= span.get("start", -1) < span.get("end", end + 1) <= end
            ):
                key = span["start"], span["end"], normalized["kind"]
                if key in values and values[key][0] != normalized["value"]:
                    conflicted = True
                if key not in values or annotation["kind"] == "formal.token":
                    values[key] = (
                        normalized["value"],
                        dict(layer=pin.values(), local_id=annotation["local_id"]),
                    )
    ordered = sorted(
        (a, b, kind, value, reference) for (a, b, kind), (value, reference) in values.items()
    )
    if (
        conflicted
        or len(ordered) != 3
        or [value[2] for value in ordered] != ["decimal", "comparator", "decimal"]
    ):
        return escaped, []
    covered = sorted([(a, b) for a, b, *_ in ordered] + list(marker_extents))
    position = start
    for left, right in covered:
        if (
            not start <= left < right <= end
            or left < position
            or text[position - start : left - start].strip()
        ):
            return escaped, []
        position = right
    if text[position - start :].strip():
        return escaped, []
    comparison = dict(
        kind="compare",
        relation=ordered[1][3],
        lhs=dict(kind="expression", language="text", expression=ordered[0][3], form="formula"),
        rhs=dict(kind="expression", language="text", expression=ordered[2][3], form="formula"),
    )
    return (
        dict(kind="not", term=comparison) if formal_operator == "not_compare" else comparison
    ), [row[4] for row in ordered]


def _primary_choices(annotation, reference):
    if reference is None:
        raise ValueError("domain projection requires exact retained primary node identity")
    report = annotation.primary_layers[reference.layer]
    body = report.payload
    row = next(
        (
            row
            for name in ("annotations", "terms", "roles", "memberships")
            for row in body[name]
            if row["local_id"] == reference.local_id
        ),
        None,
    )
    if row is None:
        raise ValueError("domain projection references absent primary node")
    return tuple(
        dict(layer=reference.layer.values(), local_id=value)
        for value in row.get("required_choices", ())
    ) + tuple(row.get("required_external_choices", ()))


def _primary_host(annotation, cue, target):
    from corpus_structure.semantic.characterization import annotation_reference

    if (
        cue.primary_ref is None
        or target.primary_ref is None
        or cue.primary_ref.layer != target.primary_ref.layer
    ):
        raise ValueError(
            "qualifier requires retained cue and host under one exact primary relation"
        )
    pin = cue.primary_ref.layer
    relations = [
        row
        for row in annotation.primary_layers[pin].payload["roles"]
        if row["owner"] == cue.primary_ref.local_id
        and row["member"] == target.primary_ref.local_id
        and row["role"] in {"host", "cross_block_host"}
    ]
    if len(relations) != 1:
        raise ValueError("qualifier has no unique actual primary host relation")
    return annotation_reference(pin, relations[0]["local_id"])


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
    version="6",
    qualifier_preflight: QualifierPreflight | None = None,
):
    """Bind each role to exact native pieces before constructing frame/attachment identities."""
    import json

    from .predicate_cross_block import CrossBlockTarget, cross_block_qualifiers

    if version != "6":
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
    attachment_issues: set[str] = set()
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
                primary_node=cue.primary_ref.values(),
                primary_marker=cue.primary_marker_ref.values(),
                primary_choices=_primary_choices(annotation, cue.primary_ref),
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
        return key, kind, host_state, source_text, len(extents) == 1, annotation, cue, extents

    def attach(selected, located, variant, target, bases, *, witness=None):
        (
            qualifier,
            kind,
            _,
            source_text,
            contiguous,
            source_annotation,
            source_cue,
            source_extents,
        ) = located
        host, reading_id = target.frame, target.reading
        primary_body = source_annotation.primary_layers[source_cue.primary_ref.layer].payload
        primary_terms = {node["local_id"]: node for node in primary_body["terms"]}
        cue_node = primary_terms[source_cue.primary_ref.local_id]
        operators = [
            primary_terms[edge["target"]]["value"]
            for edge in cue_node["children"]
            if edge["role"] == "formal_condition_operator" and "target" in edge
        ]
        lowered, condition_parts = _condition(
            kind,
            operators[0] if len(operators) == 1 else None,
            source_text,
            contiguous=contiguous,
            layers=source_annotation.primary_layers,
            projection=source_annotation.source.projection_digest,
            extents=source_extents,
            marker_extents=source_cue.basis.extents,
        )
        details: dict[str, Any] = {}
        if lowered is not None:
            details["condition"] = source_value(lowered)
            if condition_parts:
                details["primary_condition_parts"] = tuple(condition_parts)
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
        attachment = component(
            1,
            "predicate_qualifier",
            selected,
            deps,
            bases,
            qualifier_contribution_id=qualifier,
            host_contribution_id=host,
            qualifier_kind=kind,
            primary_node=_primary_host(source_annotation, source_cue, target).values(),
            primary_choices=_primary_choices(
                source_annotation, _primary_host(source_annotation, source_cue, target)
            ),
            **details,
        )
        # Local candidates stand alone. Cross-block cues have a protected
        # all-host witness population and keep their existing closure path.
        if (
            witness is None
            and qualifier_preflight is not None
            and (reason := qualifier_preflight(attachment))
        ):
            attachment_issues.add(reason)
            return
        emit(
            1,
            f"{qualifier}:{host}",
            "predicate_qualification",
            deps,
            kind="relation",
            members=members,
            endpoints=(("qualifier", qualifier), ("host", host)),
            component=attachment,
        )

    scoped_hosts = defaultdict(list)
    for annotation, result in results:
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
                    primary_ref=None,
                    *,
                    annotation=annotation,
                    selected=selected,
                    role_rows=role_rows,
                    dep=dep,
                    bases=bases,
                ):
                    if primary_ref is None:
                        raise ValueError(
                            "predicate member requires exact retained primary identity"
                        )
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
                            primary_node=primary_ref.values(),
                            primary_choices=_primary_choices(annotation, primary_ref),
                            token_indices=tokens,
                            extents=tuple(dict(start=a, end=b) for a, b in extents),
                            outcome=state if extents == span.extents else "partial",
                            **({"head_token": head} if head in tokens else {}),
                            **({"inherited_from": inherited} if inherited is not None else {}),
                        )
                    )

                from corpus_structure.semantic.characterization import annotation_reference

                primary_body = annotation.primary_layers[candidate.primary_ref.layer].payload
                primary_term = next(
                    t
                    for t in primary_body["terms"]
                    if t["local_id"] == candidate.primary_ref.local_id
                )
                primary_children = {
                    edge["role"]: annotation_reference(candidate.primary_ref.layer, edge["target"])
                    for edge in primary_term["children"]
                    if "target" in edge
                }
                member(
                    "predicate",
                    candidate.predicate,
                    predicate_token,
                    primary_ref=primary_children["predicate"],
                )
                member(
                    "focus", candidate.focus, predicate_token, primary_ref=primary_children["focus"]
                )
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
                        primary_ref=role.primary_ref,
                    )
                    if version == "6" and len(role_rows) == row_count:
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
                        primary_node=candidate.primary_ref.values(),
                        primary_choices=_primary_choices(annotation, candidate.primary_ref),
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
                        primary_node=candidate.primary_ref.values(),
                        primary_choices=_primary_choices(annotation, candidate.primary_ref),
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
                    candidate.primary_ref,
                )
                if version == "6" and scope is not None:
                    scoped_hosts[selected].append(target)
                for cue in candidate.cues:
                    located = cue_row(annotation, selected, cue, dep, bases)
                    if located is None:
                        continue
                    _, kind, host_state, *_ = located
                    if (
                        host_state != "located"
                        or predicate_token not in cue.hosts
                        or kind in {"contrast", "example", "quotation"}
                    ):
                        continue
                    attach(selected, located, cue.variant, target, bases)

    if version == "6" and scope is not None:
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

    reports = []
    definitions = zip(operations, questions, versions, strict=True)
    for index, (op, question, version) in enumerate(definitions):
        refusals = sorted(attachment_issues) if index == 1 else []
        reasons = (*issues, *refusals)
        reason = "; ".join(reasons)
        if not reason and not results:
            reason = "No retained linguistic annotation block is available."
        if reasons:
            outcome = (
                "limited" if emitted[op] else "unsupported" if unavailable or refusals else "failed"
            )
        else:
            outcome = "succeeded" if emitted[op] else "empty" if results else "not_run"
        reports.append(
            dict(
                operation_key=op,
                question=question,
                operation_version=version,
                outcome=outcome,
                **({"reason": reason} if reason else {}),
                inspected_count=sum(len(annotation.tokens) for annotation, _ in results),
                emitted_count=emitted[op],
                **(
                    {"annotation_origin_task_id": annotation_origin_task_id}
                    if annotation_origin_task_id is not None
                    else {}
                ),
                primary_layers=[
                    pin.values()
                    for pin in dict.fromkeys(
                        pin for annotation, _ in results for pin in annotation.primary_layers
                    )
                ],
                computation_dependencies=tuple(dict.fromkeys((dependency, *retained))),
            )
        )
    return tuple(reports)


@dataclass(frozen=True)
class PredicateEvidence:
    """Original predicate projection with its full inspected-operation denominator."""

    contributions: tuple[dict[str, Any], ...]
    operations: tuple[dict[str, Any], ...]
    coordinate_texts: tuple[dict[str, Any], ...]

    @property
    def inspection_complete(self) -> bool:
        return bool(self.operations) and all(
            operation["outcome"] in {"succeeded", "empty"} for operation in self.operations
        )


def declared_predicate_evidence(
    frame,
    context,
    annotations,
    *,
    dependency: str,
    annotation_errors=(),
    passages=None,
    qualifier_preflight: QualifierPreflight | None = None,
    check_active=lambda: None,
) -> PredicateEvidence:
    """Project existing admitted annotations under their real declared source pin.

    The caller owns annotation restoration/profile checks and this invocation's
    native context preparation. No source discovery, model execution, Reader or
    publication occurs here. Unavailable inspection retains its original operation
    outcomes and cannot become successful empty coverage.
    """
    from corpus_structure.semantic.declared_record_sources import DeclaredNativeFrameSource
    from corpus_structure.semantic.source_contexts import NativeSourceContext, record_source_pin

    if (
        not isinstance(frame, DeclaredNativeFrameSource)
        or not isinstance(context, NativeSourceContext)
        or context.version != 2
        or context.primary is not frame
    ):
        raise ValueError("declared predicate evidence requires its exact owned source context")
    annotations = tuple(annotations)
    if not dependency or any(annotation.source != frame.pin for annotation in annotations):
        raise ValueError("predicate annotations differ from their bound source product")
    check_active()
    value = frame.value
    items = {item["self_ref"]: item for item in value["items"]}
    results = predicate_results(frame, annotations, value["pieces"], items)
    products, coordinates = [], {}
    operations = publish_predicate_evidence(
        frame,
        context,
        record_source_pin(frame),
        dependency,
        results,
        tuple(annotation_errors),
        None,
        passages,
        products,
        coordinates,
        qualifier_preflight=qualifier_preflight,
    )
    check_active()
    return PredicateEvidence(tuple(products), operations, tuple(coordinates.values()))
