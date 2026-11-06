"""Bounded completed-cut structural reports; private proposals confer no admission."""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, JsonValue, model_validator
from sqlalchemy import Connection, Text, func, select

from corpus_structure.semantic.identity import canonical_bytes
from corpus_structure.semantic.query import bind_completed_result
from corpus_structure.semantic.refusals import SemanticRefusal
from corpus_structure.semantic.structural_products import StructuralProductReport


class DossierContinuation(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    product_id: str
    membership_digest: str
    facet_digest: str
    policy: str
    offset: int = Field(strict=True, ge=0)


def dossier_representation_page(report, *, limit=20, continuation=None):
    """Page selected members without changing immutable membership or selection.

    The enclosing completed-cut reader authenticates the report. The continuation
    binds both its source-derived membership and independently supported facets.
    Mandatory overflow is a normal pageable result, never a dropped exception.
    """
    if report.dossier is None or type(limit) is not int or not 1 <= limit <= 100:
        raise ValueError("representation page requires a dossier and limit 1..100")
    value = report.dossier
    representation = value.representation
    binding = dict(
        product_id=report.product_id,
        membership_digest=representation.membership_digest,
        facet_digest=representation.facet_digest,
        policy=representation.policy,
    )
    offset = 0
    if continuation is not None:
        cursor = DossierContinuation.model_validate(continuation)
        if any(getattr(cursor, key) != expected for key, expected in binding.items()):
            raise SemanticRefusal(
                "dossier continuation differs from exact membership/facets/policy"
            )
        offset = cursor.offset
    if offset > len(representation.selected):
        raise SemanticRefusal("dossier continuation is outside representation")
    selected = representation.selected[offset : offset + limit]
    members = {m.member_id: m for m in value.members}
    end = offset + len(selected)
    return dict(
        members=tuple(members[key] for key in selected),
        continuation=DossierContinuation(**binding, offset=end).model_dump(mode="json")
        if end < len(representation.selected)
        else None,
        mandatory_overflow=representation.mandatory_overflow,
        omitted=representation.omitted,
        missing_facets=representation.missing_facets,
    )


class StructuralRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    run_id: int = Field(strict=True, gt=0)
    cut_id: int | None = Field(default=None, strict=True, gt=0)
    kind: (
        Literal[
            "definition_components", "definition_applicability", "qualified_comparison", "dossier", "artifact_identity"
        ]
        | None
    ) = None
    after_task_id: int = Field(default=0, strict=True, ge=0)
    limit: int = Field(default=20, strict=True, ge=1, le=100)
    max_bytes: int = Field(default=1_000_000, strict=True, ge=1, le=8_000_000)
    include_publication: bool = False
    include_support: bool = False

    @model_validator(mode="after")
    def support_requires_publication(self):
        if self.include_support and not self.include_publication:
            raise ValueError("structural support requires the publication facet")
        return self


class StructuralPage(BaseModel):
    version: Literal["structural-inspection-2"] = "structural-inspection-2"
    run_id: int
    cut_id: int
    release_id: str
    reports: tuple[StructuralProductReport, ...]
    task_ids: tuple[int, ...]
    next_after_task_id: int | None
    standing: Literal["private_proposals"] = "private_proposals"
    source_coverage: Literal["declared_report_inputs_only"] = "declared_report_inputs_only"
    public_assertions: tuple[dict[str, JsonValue], ...] = ()
    publication: Literal["not_requested", "included"] = "not_requested"
    assessment_scope: Literal["published_admission_witnesses_only"] = (
        "published_admission_witnesses_only"
    )


def serve_structural_products(conn: Connection, request: StructuralRequest) -> StructuralPage:
    from corpus_structure.semantic.metadata import table

    session = bind_completed_result(conn, request.run_id)
    cut = session.completed_cut_id
    if cut is None or (request.cut_id is not None and request.cut_id != cut):
        raise SemanticRefusal("structural selection requires its exact completed cut")
    selected, origin = table("ops.task"), table("ops.task").alias("origin")
    result, membership = table("ops.task_result"), table("ops.cut_task")
    body = result.c.body["structural_product"]
    statement = (
        select(
            selected.c.id,
            origin.c.id.label("origin_id"),
            func.octet_length(body.cast(Text)).label("bytes"),
        )
        .select_from(selected)
        .join(origin, origin.c.id == func.coalesce(selected.c.reused_task_id, selected.c.id))
        .join(result, result.c.task_id == origin.c.id)
        .join(membership, (membership.c.task_id == selected.c.id) & (membership.c.cut_id == cut))
        .where(
            selected.c.run_id == request.run_id,
            selected.c.release_id == session.prepared.release_id,
            origin.c.release_id == session.prepared.release_id,
            selected.c.unit_type == "run",
            selected.c.status.in_(("done", "reused")),
            result.c.body.has_key("structural_product"),
            selected.c.id > request.after_task_id,
        )
    )
    if request.kind:
        statement = statement.where(body["kind"].astext == request.kind)
    metadata = tuple(
        conn.execute(statement.order_by(selected.c.id).limit(request.limit + 1)).mappings()
    )
    chosen = metadata[: request.limit]
    if sum(row["bytes"] for row in chosen) > request.max_bytes:
        raise SemanticRefusal("structural report selection exceeds byte budget; narrow the page")
    reports = tuple(
        StructuralProductReport.model_validate(
            conn.scalar(select(body).where(result.c.task_id == row["origin_id"]))
        )
        for row in chosen
    )
    public_assertions = ()
    if request.include_publication:
        from corpus_structure.semantic.structural_admission import read_structural_assertions

        if "StructuralPublicationPolicy" not in session.prepared.index.definitions:
            raise SemanticRefusal("selected release does not support structural publication")
        public_assertions = read_structural_assertions(
            conn,
            release_id=session.prepared.release_id,
            realization_id=session.binding.realization_id,
            product_ids=tuple(report.product_id for report in reports),
            support=request.include_support,
            max_bytes=request.max_bytes,
        )
    page = StructuralPage(
        run_id=request.run_id,
        cut_id=cut,
        release_id=session.prepared.release_id,
        reports=reports,
        task_ids=tuple(row["id"] for row in chosen),
        next_after_task_id=chosen[-1]["id"] if len(metadata) > request.limit else None,
        public_assertions=public_assertions,
        publication="included" if request.include_publication else "not_requested",
    )
    if len(canonical_bytes(page.model_dump(mode="json"))) > request.max_bytes:
        raise SemanticRefusal("structural response exceeds byte budget; narrow the page")
    return page
