"""Bounded operator diagnosis through an explicitly selected source and producer chain."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from corpus_structure.semantic.declared_structural_references import DeclaredStructuralSource
from corpus_structure.semantic.selected_structural_projection import (
    producer,
    selected_contextual,
    selected_root,
    structural_report,
)

from .selected_structural import (
    SelectedStructuralRoot,
    StructuralReadRequest,
    bounded_result,
    structural_scope,
)


class SelectedOpportunity(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    source: DeclaredStructuralSource
    pointer: str = Field(pattern=r"^#/.+")
    start: int = Field(strict=True, ge=0)
    end: int = Field(strict=True, gt=0)

    @model_validator(mode="after")
    def extent(self):
        if self.start >= self.end:
            raise ValueError("opportunity requires a nonempty native source extent")
        return self


class SelectedJourneyLayer(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    layer: Literal["artifact", "contextual", "comparison", "dossier"]
    root: SelectedStructuralRoot
    case_id: str | None = Field(default=None, min_length=1)
    target_id: str | None = Field(default=None, min_length=1)

    @model_validator(mode="after")
    def exact_case(self):
        if self.layer in ("contextual", "comparison") and self.case_id is None:
            raise ValueError("contextual and comparison layers require the exact case identity")
        if self.layer in ("comparison", "dossier") and self.target_id is not None:
            raise ValueError("target selection applies only to artifact and contextual layers")
        return self


class SelectedSourceDecisionJourneyRequest(StructuralReadRequest):
    opportunity: SelectedOpportunity
    layers: tuple[SelectedJourneyLayer, ...] = Field(min_length=1, max_length=4)

    @model_validator(mode="after")
    def distinct_layers(self):
        names = {item.layer for item in self.layers}
        if len(names) != len(self.layers) or ("dossier" in names and "comparison" not in names):
            raise ValueError(
                "journey requires distinct layers and a comparison for dossier binding"
            )
        if self.project_id != self.opportunity.source.project_id:
            raise ValueError("journey opportunity belongs to another reader project")
        return self


def selected_source_state(opportunity, source):
    """Locate original-relative coordinates without treating a projection omission as absence."""
    pointer, separator, cell = opportunity.pointer.partition("/data/table_cells/")
    if separator and not cell.isdecimal():
        raise ValueError("invalid native table-cell pointer")
    item = next((item for item in source["items"] if item["self_ref"] == pointer), None)
    if item is None:
        return "outside_selection", ()
    if separator:
        cells = item.get("data", {}).get("table_cells", ())
        if int(cell) >= len(cells):
            raise ValueError("native table-cell pointer is outside its original item")
        item = cells[int(cell)]
    text = item.get("text")
    if not isinstance(text, str) or opportunity.end > len(text):
        raise ValueError("opportunity escapes its original native text")
    quote = text[opportunity.start : opportunity.end]
    projected = []
    for piece in source["pieces"]:
        if (
            piece["kind"] != "native_text"
            or piece.get("item_ref") != pointer
            or (str(piece["cell_index"]) if piece.get("cell_index") is not None else "") != cell
            or opportunity.end > piece["end"] - piece["start"]
        ):
            continue
        start, end = piece["start"] + opportunity.start, piece["start"] + opportunity.end
        if source["text"][start:end] != quote:
            raise ValueError("source projection differs from original native opportunity")
        projected.append((start, end))
    return ("represented" if projected else "omitted_from_projection"), tuple(projected)


def _selected_anchor(opportunity, pin, anchors):
    return opportunity.source.matches_pin(pin) and any(
        anchor.get("pointer") == opportunity.pointer
        and anchor.get("space") == "native"
        and anchor.get("precision") == "exact"
        and anchor["start"] <= opportunity.start < opportunity.end <= anchor["end"]
        for anchor in anchors
    )


def selected_journey_layer(layer, opportunity, body, projected, *, comparison=None):
    """Project actual retained judgments; no producer or NLP runs at read time."""
    if layer.layer == "artifact":
        artifact = body.get("artifact_identity")
        if artifact is None:
            return None
        records = [
            row
            for row in artifact["records"]
            if layer.case_id in (None, row["occurrence_id"], row["contribution_id"])
            and _selected_anchor(
                opportunity,
                row["source_contribution"].get("pin", {}),
                row["source_contribution"].get("anchors", ()),
            )
        ]
        ids = {row["contribution_id"] for row in records}
        return bool(records), dict(
            occurrences=records,
            route_counts=artifact["route_counts"],
            pairs=[
                row
                for row in artifact["pairs"]
                if ids.intersection((row["left"], row["right"]))
                and layer.target_id in (None, row["left"], row["right"])
            ],
            directed_references=[
                row
                for row in artifact.get("external_nominations", ())
                if ids.intersection((row["left"], row["right"]))
            ],
            declared_relationships=[
                row
                for row in artifact.get("declared_relationships") or ()
                if row["source_id"] in ids
                or ids.intersection(t["record_id"] for t in row["targets"])
            ],
            reference_resolutions=[
                row for row in artifact.get("explicit_references", ()) if row["attachment"] in ids
            ],
        )
    if layer.layer == "contextual":
        candidates, decision = body["candidate_list"], body["relationship_decision"]
        matched = layer.case_id == candidates["occurrence_id"] and _selected_anchor(
            opportunity, body["source_pin"], body["anchors"]
        )
        return matched, dict(
            candidate_list=candidates if matched else None,
            relationship_decision=decision if matched else None,
            selected_target_eligible=(
                any(
                    target["target_id"] == layer.target_id
                    for target in body["inventory"]["targets"]
                )
                if matched and layer.target_id is not None
                else None
            ),
        )
    if layer.layer == "comparison":
        value = body.get("comparison")
        if value is None:
            return None
        passages = {
            row["passage_id"]
            for row in body["inputs"]["passages"]
            if row["source_ref"] == opportunity.source.identity
            and any(row["start"] <= start < end <= row["end"] for start, end in projected)
        }
        sides = []
        for side in ("left", "right"):
            reading, focus = value[side + "_reading"], value.get(side + "_focus")
            if value[side + "_id"] not in passages or reading["contribution_id"] != layer.case_id:
                continue
            if focus is None:
                return None
            if any(focus["start"] <= start < end <= focus["end"] for start, end in projected):
                sides.append(dict(side=side, reading=reading, focus=focus))
        return bool(sides), dict(sides=sides, comparison=value)
    dossier = body.get("dossier")
    if dossier is None or comparison is None:
        return None
    comparison_ref, sides = comparison
    if comparison_ref not in dossier["predecessors"]:
        return None
    members = [
        member
        for member in dossier["members"]
        if member.get("comparison_binding") is not None
        and member["comparison_binding"]["comparison_ref"] == comparison_ref
        and member["comparison_binding"]["side"] in sides
        and layer.case_id in (None, member["member_id"])
    ]
    display = set(dossier["representation"]["selected"])
    return bool(members), dict(
        membership=members,
        display=[member["member_id"] for member in members if member["member_id"] in display],
    )


def inspect_selected_source_journey(conn, request: SelectedSourceDecisionJourneyRequest):
    from corpus_structure.semantic.data_operation_model import json_context_meaning
    from corpus_structure.semantic.declared_structural_references import DeclaredStructuralRef

    from .selected_math import _source_for_interpretation

    source_ref = request.opportunity.source
    with structural_scope(
        conn,
        request,
        roots=tuple(layer.root for layer in request.layers),
        source_products=(source_ref.source_product,),
    ) as scope:
        frozen = _source_for_interpretation(
            scope.prepared,
            source_ref,
            scope.index.mapping("kb.data_product", ("id",)),
            scope.index.mapping("kb.data_product_member", ("product_id", "member_id")),
        )
        status, projected = selected_source_state(request.opportunity, frozen.value)
        requested = {layer.layer: layer for layer in request.layers}
        answers, comparison = [], None
        for name in ("artifact", "contextual", "comparison", "dossier"):
            if name not in requested:
                answers.append(dict(layer=name, status="unrequested", evidence={}))
                continue
            layer = requested[name]
            selected = selected_root(scope, layer.root)
            if selected is None:
                answers.append(
                    dict(
                        layer=name,
                        status="outside_selection",
                        root=layer.root.model_dump(),
                        evidence={},
                    )
                )
                continue
            report = None if name == "contextual" else structural_report(scope, selected)
            body = (
                selected_contextual(scope, selected)
                if report is None
                else report.model_dump(mode="python", exclude_none=True)
            )
            result = selected_journey_layer(
                layer, request.opportunity, body, projected, comparison=comparison
            )
            if name == "comparison" and result is not None:
                assert report is not None
                context = selected.context
                reference = DeclaredStructuralRef(
                    product_id=selected.reference.product_id,
                    member_id=selected.reference.member_id,
                    kind_contract=selected.reference.kind_contract,
                    project_id=context.project_id,
                    subject=context.subject,
                    subject_definition=context.subject_definition,
                    original_source=context.original_source,
                    analyzed_scope_meaning=json_context_meaning(context.analyzed_scope).decode(),
                    structural_id=report.product_id,
                )
                comparison = (
                    reference.model_dump(mode="python", exclude_none=True),
                    {row["side"] for row in result[1]["sides"]},
                )
            answers.append(
                dict(
                    layer=name,
                    status="unavailable"
                    if result is None
                    else "observed"
                    if result[0]
                    else "inspected_empty",
                    producer=producer(selected),
                    evidence={} if result is None else result[1],
                )
            )
        return bounded_result(
            request,
            dict(
                format="selected-source-decision-journey-v1",
                cut_id=scope.cut.identity,
                cut=scope.cut.record,
                implementation=scope.implementation,
                opportunity=request.opportunity.model_dump(mode="python"),
                source_capture=status,
                layers=answers,
                standing="private_proposal",
                public_admission="not-established",
            ),
        )
