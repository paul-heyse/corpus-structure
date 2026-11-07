"""Bounded operator diagnosis through an explicitly selected source and producer chain."""

from __future__ import annotations

from collections.abc import Iterator
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, JsonValue, model_validator
from sqlalchemy import select, text

from corpus_structure.semantic.metadata import table
from corpus_structure.semantic.pdf_record_reader import PublishedReadBudget
from corpus_structure.semantic.query import bind_completed_result
from corpus_structure.semantic.refusals import SemanticRefusal
from corpus_structure.semantic.source_views import load_source_view
from corpus_structure.semantic.structural_products import ExternalSourceRef
from corpus_structure.serve.protocol import Positioned, QueryContext, Scope
from corpus_structure.serve.structural_gaps import GapTask, _task

Positive = Annotated[int, Field(strict=True, gt=0)]
Layer = Literal["artifact", "contextual", "comparison", "dossier"]
Status = Literal["observed", "inspected_empty", "unavailable", "outside_selection", "unrequested"]
METHODS = {
    "artifact": "structure.artifact_identity",
    "contextual": "retrieve.contextual",
    "comparison": "structure.compare",
    "dossier": "structure.dossier",
}


class Opportunity(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    source: ExternalSourceRef
    pointer: str = Field(pattern=r"^#/.+")
    start: int = Field(strict=True, ge=0)
    end: Positive

    @model_validator(mode="after")
    def extent(self):
        if self.start >= self.end:
            raise ValueError("opportunity requires a nonempty native source extent")
        return self


class JourneyTask(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    layer: Layer
    run_id: Positive
    cut_id: Positive
    task_id: Positive
    case_id: str | None = Field(default=None, min_length=1)
    target_id: str | None = Field(default=None, min_length=1)

    @model_validator(mode="after")
    def exact_case(self):
        if self.layer in ("contextual", "comparison") and self.case_id is None:
            raise ValueError("contextual and comparison layers require the exact case identity")
        if self.layer in ("comparison", "dossier") and self.target_id is not None:
            raise ValueError("target selection applies only to artifact and contextual layers")
        return self


class SourceDecisionJourneyParams(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    opportunity: Opportunity
    layers: tuple[JourneyTask, ...] = Field(min_length=1, max_length=4)

    @model_validator(mode="after")
    def distinct_layers(self):
        names = {item.layer for item in self.layers}
        if len(names) != len(self.layers) or ("dossier" in names and "comparison" not in names):
            raise ValueError(
                "journey requires distinct layers and a comparison for dossier binding"
            )
        return self


class JourneyLayerAnswer(BaseModel):
    layer: Layer
    status: Status
    producer: dict[str, JsonValue] | None = None
    evidence: dict[str, JsonValue]


class SourceDecisionJourneyAnswer(BaseModel):
    opportunity: Opportunity
    source_capture: Literal["represented", "omitted_from_projection", "outside_selection"]
    layers: tuple[JourneyLayerAnswer, ...]


class SourceDecisionJourneyQuery:
    name = "source_decision_journey"
    version = "source-decision-journey-1"
    params = SourceDecisionJourneyParams
    result = SourceDecisionJourneyAnswer

    def scope(self, ctx: QueryContext, p: SourceDecisionJourneyParams) -> Scope:
        return Scope.run()

    def validate_position(self, position):
        if position not in (None, "done"):
            raise SemanticRefusal("invalid source-decision journey continuation")

    def rows(
        self, ctx: QueryContext, p: SourceDecisionJourneyParams, after: JsonValue = None
    ) -> Iterator[Positioned]:
        self.validate_position(after)
        if after == "done":
            return
        runs = table("ops.run")
        if ctx.conn.scalar(select(runs.c.project_id).where(runs.c.id == ctx.run_id)) != (
            p.opportunity.source.project_id
        ):
            raise SemanticRefusal("journey opportunity belongs to another reader project")
        source, tasks = capture_source_decision_journey(ctx.conn, p)
        yield Positioned(source_decision_journey(p, source, tasks), "done")


def capture_source_decision_journey(conn, params, *, source_loader=None, budget=None):
    """Capture trusted raw input in the caller's single read-only snapshot."""
    ref = params.opportunity.source
    session = bind_completed_result(conn, ref.run_id)
    if (
        session.completed_cut_id != ref.cut_id
        or session.binding.release_id != ref.release_id
        or session.binding.data_revision != ref.result_revision
    ):
        raise SemanticRefusal("journey opportunity differs from its original completed result")
    conn.execute(
        text("SELECT ops.validate_structural_source(CAST(:source AS jsonb))"),
        {"source": ref.model_dump_json()},
    )
    if budget is None:
        budget = PublishedReadBudget(10000, 32_000_000)
    if source_loader is None:
        view = load_source_view(conn, ref.source_view_id, analysis=False, read_budget=budget)
        from dataclasses import asdict

        source = {"ref": asdict(view.ref), "text": view.text, "context": view.context()}
    else:
        source = source_loader(ref.source_view_id)
    tasks = {}
    for layer in params.layers:
        _, pin = _task(
            conn,
            GapTask(run_id=layer.run_id, cut_id=layer.cut_id, task_id=layer.task_id),
            METHODS[layer.layer],
        )
        if pin["project_id"] != ref.project_id:
            raise SemanticRefusal("journey producer belongs to a different project")
        body = None
        if pin["cut_member"] and pin["task_status"] in {"done", "empty", "reused"}:
            reports = table("ops.task_result")
            statement = select(reports.c.body).where(reports.c.task_id == pin["origin_task_id"])
            budget.preflight(conn, statement)
            body = conn.scalar(statement)
            if body is not None:
                budget.value(body)
        tasks[layer.layer] = pin, body
    return source, tasks


def _source_state(opportunity, source):
    ref, context = source["ref"], source["context"]
    original = opportunity.source
    product = ref["native_product"]
    if (
        ref["id"],
        product["task_id"],
        product["product_key"],
        product["content_digest"],
        ref["projection_digest"],
        ref["recipe_digest"],
    ) != (
        original.source_view_id,
        original.native_task_id,
        original.native_product_key,
        original.native_content_digest,
        original.projection_digest,
        original.recipe_digest,
    ):
        raise ValueError("journey source differs from exact original native custody")
    if (3 if "integrated_context_json" in context else 2) != original.coordinate_version:
        raise ValueError("journey source differs from its original coordinate ABI")
    pointer, sep, cell_index = opportunity.pointer.partition("/data/table_cells/")
    if sep and not cell_index.isdecimal():
        raise ValueError("journey opportunity has an invalid native cell pointer")
    selected = {item["self_ref"]: item for item in context["items"]}
    item = selected.get(pointer)
    if item is None:
        return "outside_selection", ()
    if sep:
        cells = item.get("data", {}).get("table_cells", ())
        if int(cell_index) >= len(cells):
            raise ValueError("journey opportunity has an invalid native cell pointer")
        item = cells[int(cell_index)]
    native_text = item.get("text")
    if not isinstance(native_text, str) or opportunity.end > len(native_text):
        raise ValueError("journey opportunity escapes its original native text")
    quote = native_text[opportunity.start : opportunity.end]
    projected = []
    for piece in context["pieces"]:
        if (
            piece["kind"] != "native_text"
            or piece["item_ref"] != pointer
            or (str(piece["cell_index"]) if piece.get("cell_index") is not None else "")
            != cell_index
            or opportunity.end > piece["end"] - piece["start"]
        ):
            continue
        start, end = piece["start"] + opportunity.start, piece["start"] + opportunity.end
        if source["text"][start:end] != quote:
            raise ValueError("journey source projection differs from native extent")
        projected.append((start, end))
    return ("represented" if projected else "omitted_from_projection"), tuple(projected)


def _matches_anchor(opportunity, contribution):
    source = opportunity.source
    pin = contribution.get("pin", {})
    return (
        pin.get("native_product_task_id"),
        pin.get("product_key"),
        pin.get("product_digest"),
    ) == (source.native_task_id, source.native_product_key, source.native_content_digest) and any(
        anchor.get("pointer") == opportunity.pointer
        and anchor.get("space") == "native"
        and anchor.get("precision") == "exact"
        and anchor["start"] <= opportunity.start < opportunity.end <= anchor["end"]
        for anchor in contribution.get("anchors", ())
    )


def _artifact(layer, opportunity, product):
    artifact = product.get("artifact_identity")
    if artifact is None:
        return None
    records = [
        row
        for row in artifact["records"]
        if (
            layer.case_id is None or layer.case_id in (row["occurrence_id"], row["contribution_id"])
        )
        and _matches_anchor(opportunity, row["source_contribution"])
    ]
    ids = {row["contribution_id"] for row in records}
    pairs = [
        row
        for row in artifact["pairs"]
        if ids.intersection((row["left"], row["right"]))
        and (layer.target_id is None or layer.target_id in (row["left"], row["right"]))
    ]
    return bool(records), dict(
        occurrences=[
            {key: row[key] for key in ("contribution_id", "occurrence_id", "citations", "artifact")}
            for row in records
        ],
        route_counts=artifact["route_counts"],
        pairs=pairs,
        directed_references=[
            row
            for row in artifact.get("external_nominations", ())
            if ids.intersection((row["left"], row["right"]))
            and (layer.target_id is None or layer.target_id in (row["left"], row["right"]))
        ],
        declared_relationships=[
            row
            for row in artifact.get("declared_relationships", ())
            if row["source_id"] in ids or ids.intersection(t["record_id"] for t in row["targets"])
        ],
        reference_resolutions=[
            row for row in artifact.get("reference_resolutions", ()) if row["attachment"] in ids
        ],
    )


def _contextual(layer, opportunity, body):
    rows = [
        row
        for row in body.get("contributions", ())
        if layer.case_id in (row.get("occurrence_id"), row["contribution_id"])
        and _matches_anchor(opportunity, row)
    ]
    reports = [
        operation["contextual_enrichment"]
        for operation in body.get("contribution_operations", ())
        if operation.get("contextual_enrichment") is not None
    ]
    if not reports:
        return None
    occurrences = {row.get("occurrence_id") for row in rows}
    inventories = {
        item["inventory_id"]: item for report in reports for item in report["inventories"]
    }
    lists = [
        row
        for report in reports
        for row in report["candidate_lists"]
        if row["occurrence_id"] in occurrences
    ]
    return bool(rows), dict(
        occurrences=[row["contribution_id"] for row in rows],
        eligibility=[
            dict(
                inventory_id=row["inventory_id"],
                eligible_target_count=row["eligible_target_count"],
                selected_target_eligible=any(
                    candidate["target_id"] == layer.target_id
                    for candidate in inventories[row["inventory_id"]]["targets"]
                )
                if layer.target_id is not None
                else None,
            )
            for row in lists
        ],
        routes=[
            {
                **route,
                "hits": [
                    hit
                    for hit in route["hits"]
                    if layer.target_id is None or hit["target_id"] == layer.target_id
                ],
            }
            for row in lists
            for route in row["channel_results"]
        ],
        decisions=[
            row
            for report in reports
            for row in report["relationship_decisions"]
            if row["occurrence_id"] in occurrences
        ],
    )


def _comparison(layer, opportunity, product, projected):
    from corpus_structure.semantic.structural_products import StructuralProductReport

    comparison = product.get("comparison")
    if comparison is None:
        return None
    report = StructuralProductReport.model_validate(product)
    scoped = {
        passage.passage_id
        for passage in report.inputs.passages
        if passage.source_ref == opportunity.source.identity
        and any(passage.start <= start < end <= passage.end for start, end in projected)
    }
    sides = []
    for side in ("left", "right"):
        reading = comparison.get(side + "_reading")
        focus = comparison.get(side + "_focus")
        passage = comparison[side + "_id"]
        if (
            passage in scoped
            and reading
            and layer.case_id == reading["contribution_id"]
            and focus is None
        ):
            return None
        if (
            passage in scoped
            and reading is not None
            and layer.case_id == reading["contribution_id"]
            and focus is not None
            and any(focus["start"] <= start < end <= focus["end"] for start, end in projected)
        ):
            sides.append(dict(side=side, passage_id=passage, reading=reading, focus=focus))
    return bool(sides), dict(
        comparison_product_id=report.product_id,
        sides=sides,
        applicability=comparison["applicability"],
        applicability_reason=comparison["applicability_reason"],
        dimensions=comparison["dimensions"],
    )


def _dossier(layer, product, comparison, comparison_pin):
    dossier = product.get("dossier")
    if dossier is None or comparison is None or not comparison["sides"]:
        return None

    def exact_predecessor(ref):
        return ref["product_id"] == comparison["comparison_product_id"] and all(
            ref[key] == comparison_pin[key]
            for key in (
                "project_id",
                "run_id",
                "cut_id",
                "selected_task_id",
                "origin_task_id",
                "release_id",
                "result_revision",
                "runtime_fingerprint",
            )
        )

    if not any(exact_predecessor(ref) for ref in dossier["predecessors"]):
        return None
    sides = {row["side"] for row in comparison["sides"]}
    members = []
    for member in dossier["members"]:
        binding = member.get("comparison_binding")
        if binding is None or binding["side"] not in sides:
            continue
        ref = binding["comparison_ref"]
        if exact_predecessor(ref) and (
            layer.case_id is None or layer.case_id == member["member_id"]
        ):
            members.append(member)
    display = set(dossier["representation"]["selected"])
    return bool(members), dict(
        membership=members,
        display=[member["member_id"] for member in members if member["member_id"] in display],
    )


def source_decision_journey(params, source, tasks):
    """Project only the requested, physically or semantically joined cases."""
    status, projected = _source_state(params.opportunity, source)
    requests = {request.layer: request for request in params.layers}
    layers = []
    comparison = comparison_pin = None
    for name in ("artifact", "contextual", "comparison", "dossier"):
        if name not in requests:
            layers.append(JourneyLayerAnswer(layer=name, status="unrequested", evidence={}))
            continue
        layer = requests[name]
        pin, body = tasks[name]
        result = None
        if not pin["cut_member"]:
            outcome = "outside_selection"
        elif body is None:
            outcome = "unavailable"
        else:
            product = body.get("structural_product") or {}
            if name == "artifact":
                result = _artifact(layer, params.opportunity, product)
            elif name == "contextual":
                result = _contextual(layer, params.opportunity, body)
            elif name == "comparison":
                result = _comparison(layer, params.opportunity, product, projected)
                if result is not None:
                    comparison, comparison_pin = result[1], pin
            else:
                result = _dossier(layer, product, comparison, comparison_pin)
            outcome = (
                "unavailable" if result is None else "observed" if result[0] else "inspected_empty"
            )
        layers.append(
            JourneyLayerAnswer(
                layer=name,
                status=outcome,
                producer=pin,
                evidence=result[1] if result is not None else {},
            )
        )
    return SourceDecisionJourneyAnswer(
        opportunity=params.opportunity, source_capture=status, layers=tuple(layers)
    )
