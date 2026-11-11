"""Located procedure roles from retained dependency columns, without reparsing text.

These are linguistic proposals. Voice, coordination, negation and clause markers
are retained as evidence; grammatical roles never authorize semantic publication.
"""

from __future__ import annotations

from typing import Literal, TypedDict

from .predicate_frames import (
    PREDICATE_FRAME_VERSION as PREDICATE_FRAME_VERSION,
)
from .predicate_frames import (
    FrameCue as FrameCue,
)
from .predicate_frames import (
    PredicateFrame as PredicateFrame,
)
from .predicate_frames import (
    frames_from_annotation as frames_from_annotation,
)
from .predicate_frames import (
    predicate_frame_result as predicate_frame_result,
)
from .predicate_frames import (
    predicate_frames as predicate_frames,
)

type RoleSpan = tuple[int, int]


class ProcedureFrame(TypedDict):
    action: RoleSpan
    actor: tuple[RoleSpan, ...]
    object: tuple[RoleSpan, ...]
    modality: tuple[RoleSpan, ...]
    conditions: list[RoleSpan]
    exceptions: list[RoleSpan]
    orders: list[tuple[RoleSpan, RoleSpan]]
    voice: Literal["active", "passive"]
    polarity: Literal["positive", "negative", "negative_scope_unresolved"]
    behavior: Literal["prescribed", "example", "described_or_example_unresolved"]
    clause_role: Literal["subordinate", "main_or_coordinate"]
    dependency: str


def procedure_frames(text, annotations) -> tuple[ProcedureFrame, ...]:
    """Project retained primary predicate roles into the domain's procedure shape."""
    frames: list[ProcedureFrame] = []
    for product in annotations:
        if not getattr(product, "primary_layers", None):
            continue
        result = predicate_frames(text, (product,))
        for primary in result.frames:
            if primary.voice not in {"active", "passive"}:
                continue
            roles = {role.name: role for role in primary.roles if role.status == "located"}

            def extents(name, *, roles=roles):
                return roles[name].span.extents if name in roles else ()

            cues = primary.cues
            modalities = tuple(
                extent for cue in cues if cue.kind == "modality" for extent in cue.span.extents
            )
            orders = []
            for cue in cues:
                if (
                    cue.kind == "order"
                    and cue.variant in {"before", "after"}
                    and cue.status == "located"
                    and cue.component is not None
                    and cue.origin is not None
                ):
                    main = product.tokens[cue.origin]
                    subordinate = product.tokens[cue.component]
                    first, second = (
                        ((main.start, main.end), (subordinate.start, subordinate.end))
                        if cue.variant == "before"
                        else ((subordinate.start, subordinate.end), (main.start, main.end))
                    )
                    orders.append((first, second))
            primary_body = product.primary_layers[primary.primary_ref.layer].payload
            terms = {term["local_id"]: term for term in primary_body["terms"]}
            clause = next(
                (
                    terms[edge["target"]]["value"]
                    for edge in terms[primary.primary_ref.local_id]["children"]
                    if edge["role"] == "clause_role"
                ),
                "main_or_coordinate",
            )
            if clause not in {"subordinate", "main_or_coordinate"}:
                raise ValueError("unknown retained clause role")
            frames.append(
                dict(
                    action=primary.predicate.extents[0],
                    actor=extents("actor"),
                    object=extents("object"),
                    modality=modalities,
                    conditions=[
                        extent
                        for cue in cues
                        if cue.kind in {"condition", "assumption"}
                        for extent in cue.span.extents
                    ],
                    exceptions=[
                        extent
                        for cue in cues
                        if cue.kind == "exception"
                        for extent in cue.span.extents
                    ],
                    orders=orders,
                    voice=primary.voice,
                    polarity=primary.polarity
                    if primary.polarity in {"positive", "negative", "negative_scope_unresolved"}
                    else "negative_scope_unresolved",
                    behavior="prescribed"
                    if primary.interpretation == "prescribed_action"
                    else "example"
                    if primary.interpretation == "example"
                    else "described_or_example_unresolved",
                    clause_role=clause,
                    dependency=product.dependency_digest,
                )
            )
    return tuple(frames)


def captured_formula_symbols(
    text,
    *,
    primary_layers=None,
    projection=None,
    source_start=None,
    native_pointer=None,
    representation="source_text",
    parent_occurrence=None,
    seconds=None,
    source_view_id=None,
):
    """Read positioned retained math symbols under an exact original field address.

    ``start``/``end`` are local to the explicitly named input representation.
    Recognized-LaTeX interiors retain their parent correspondence and do not gain
    native PDF/source-character authority. Missing metadata never reruns a parser.
    """
    if primary_layers is None or projection is None or source_start is None:
        return (), "unsupported"
    from corpus_structure.semantic.characterization import annotation_reference

    roots = []
    for pin, report in primary_layers.items():
        body = report.payload
        occurrences = {o["local_id"]: o for o in body["occurrences"]}
        for annotation in body["annotations"]:
            value = annotation.get("formal_input")
            if (
                value is None
                or annotation["family"] != "formal.math"
                or value["text"] != text
                or value["representation"] != representation
            ):
                continue
            parent = value["parent_occurrence"]
            if parent_occurrence is not None and parent != parent_occurrence:
                continue
            extents = occurrences[parent]["extents"]
            if (
                not extents
                or extents[0].get("start") != source_start
                or any(
                    e["projection"] != projection
                    or (source_view_id is not None and e["source_view_id"] != source_view_id)
                    for e in extents
                )
            ):
                continue
            if native_pointer is not None and any(
                e["native_pointer"] != native_pointer for e in extents
            ):
                continue
            roots.append((pin, body, annotation, value))
    if len(roots) != 1:
        return (), "ambiguous" if roots else "unsupported"
    pin, body, root, value = roots[0]
    if value["syntax_outcome"] != "complete":
        return (), "ambiguous" if value["syntax_outcome"] == "ambiguous" else "unsupported"
    if value.get("symbol_outcome") != "complete":
        return (), "unsupported"
    nodes = {a["local_id"]: a for a in body["annotations"]}
    symbols = []
    for annotation in nodes.values():
        formal = annotation.get("formal")
        if (
            annotation["kind"] != "formal.symbol"
            or formal is None
            or formal["input_id"] != root["local_id"]
        ):
            continue
        normalized = formal.get("normalized", {})
        if normalized.get("kind") != "identifier":
            continue
        parent_id = formal.get("symbol_parent")
        parent = nodes.get(parent_id, {}).get("formal", {}).get("normalized", {})
        symbols.append(
            dict(
                start=formal["start"],
                end=formal["end"],
                name=normalized["value"],
                syntax_parent=parent.get("value"),
                **(
                    {"syntax_parent_node": annotation_reference(pin, parent_id).values()}
                    if parent_id is not None
                    else {}
                ),
                primary_node=annotation_reference(pin, annotation["local_id"]).values(),
                parent_occurrence=value["parent_occurrence"],
                coordinate_space="native_projection"
                if representation == "source_text"
                else "recognized_latex",
            )
        )
    # A successful symbolic syntax with unprojected native symbol metadata is
    # incomplete for this consumer, not proof that the formula has no symbols.
    if not symbols and any(
        a.get("formal", {}).get("input_id") == root["local_id"]
        and "SYMBOL" in a.get("formal", {}).get("rule", "")
        for a in nodes.values()
    ):
        return (), "unsupported"
    return tuple(sorted(symbols, key=lambda row: (row["start"], row["end"], row["name"]))), "parsed"
