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


class StructuralExportRequest(BaseModel):
    """Exact completed-cut selection with a separately bounded file-export payload.

    Full retained membership may exceed a transport page. Export owns its cumulative
    file budget; interactive inspection keeps the narrower StructuralRequest policy.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)
    run_id: int = Field(strict=True, gt=0)
    cut_id: int | None = Field(default=None, strict=True, gt=0)
    kind: (
        Literal[
            "definition_components",
            "definition_applicability",
            "clause_classification",
            "qualified_comparison",
            "dossier",
            "artifact_identity",
        ]
        | None
    ) = None
    after_task_id: int = Field(default=0, strict=True, ge=0)
    selected_task_id: int | None = Field(
        default=None, strict=True, gt=0, exclude_if=lambda value: value is None
    )
    limit: int = Field(default=20, strict=True, ge=1, le=100)
    max_bytes: int = Field(default=134_217_728, strict=True, ge=1)
    include_publication: bool = False
    include_support: bool = False

    @model_validator(mode="after")
    def support_requires_publication(self):
        if self.include_support and not self.include_publication:
            raise ValueError("structural support requires the publication facet")
        return self


class StructuralRequest(StructuralExportRequest):
    """Interactive structural report delivery; large dossiers use representation pages."""

    max_bytes: int = Field(default=1_000_000, strict=True, ge=1, le=8_000_000)


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
    return _read_structural_page(conn, request)


def read_structural_export_page(
    conn: Connection, request: StructuralExportRequest
) -> StructuralPage:
    """Read an exact file-export selection under its explicit payload budget."""
    return _read_structural_page(conn, request)


def _read_structural_page(conn: Connection, request: StructuralExportRequest) -> StructuralPage:
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
    if request.selected_task_id is not None:
        statement = statement.where(selected.c.id == request.selected_task_id)
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


class DossierRepresentationRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    run_id: int = Field(strict=True, gt=0)
    task_id: int = Field(strict=True, gt=0)
    cut_id: int | None = Field(default=None, strict=True, gt=0)
    limit: int = Field(default=20, strict=True, ge=1, le=100)
    max_bytes: int = Field(default=1_000_000, strict=True, ge=1, le=8_000_000)
    continuation: DossierContinuation | None = None


class DossierRepresentationPage(BaseModel):
    version: Literal["dossier-representation-1"] = "dossier-representation-1"
    run_id: int
    cut_id: int
    task_id: int
    product_id: str
    policy: str
    membership_digest: str
    facet_digest: str
    members: tuple[dict[str, JsonValue], ...]
    citations: tuple[dict[str, JsonValue], ...]
    supported_facets: tuple[dict[str, JsonValue], ...]
    full_member_count: int
    omitted_member_count: int
    missing_facet_count: int
    mandatory_overflow: bool
    continuation: DossierContinuation | None = None
    standing: Literal["private_proposals"] = "private_proposals"


_DOSSIER_SLICE_SQL = """
WITH source AS (
 SELECT body->'structural_product' report FROM ops.task_result WHERE task_id=:origin_id
), chosen AS (
 SELECT id,ord FROM source,
 jsonb_array_elements(report#>'{dossier,representation,selected}') WITH ORDINALITY choice(id,ord)
 WHERE ord>:offset AND ord<=:end_offset
), selected_members AS (
 SELECT m,ord FROM source,chosen,jsonb_array_elements(report#>'{dossier,members}') m
 WHERE m->'member_id'=chosen.id
), selected_citations AS (
 SELECT DISTINCT jsonb_build_object('member_id',m->'member_id','source',s,
 'citation',citation_->'span','scope',m->'scope','effective_version',m->'effective_version',
 'contribution_id',citation_->'contribution_id','source_pointer',citation_->'source_pointer') c
 FROM source,selected_members,jsonb_array_elements(report#>'{inputs,passages}') p,
 jsonb_array_elements(report#>'{inputs,sources}') s,
 LATERAL jsonb_array_elements(COALESCE(
 nullif(m->'contribution_citations','null'::jsonb),jsonb_build_array(
 jsonb_build_object('span',m->'citation')))) citation_
 WHERE p->'passage_id'=citation_->'span'->'passage_id'
 AND p->>'source_ref'=encode(sha256(convert_to(data.canonical_json(s),'UTF8')),'hex')
 UNION
 SELECT DISTINCT jsonb_build_object('member_id',m->'member_id',
  'source',m->'comparison_binding'->'opposite_source',
  'citation',m->'comparison_binding'->'opposite_citation','context','opposite_comparison_side')
 FROM selected_members WHERE jsonb_typeof(m->'comparison_binding')='object'
), payload AS (
 SELECT jsonb_build_object(
  'members',COALESCE((SELECT jsonb_agg(m ORDER BY ord) FROM selected_members),'[]'),
  'citations',COALESCE((SELECT jsonb_agg(c ORDER BY data.canonical_json(c))
   FROM selected_citations),'[]'),
  'supported_facets',COALESCE((SELECT jsonb_agg(f ORDER BY f->>'facet_id')
   FROM source,jsonb_array_elements(report#>'{dossier,supported_facets}')f
   WHERE EXISTS(SELECT FROM chosen WHERE chosen.id=f->'member_id')),'[]')) body
) SELECT {projection} FROM payload
"""


def serve_dossier_representation(
    conn: Connection, request: DossierRepresentationRequest
) -> DossierRepresentationPage:
    """Read selected exact members only, after immutable metadata/byte admission."""
    from sqlalchemy import text

    from corpus_structure.semantic.metadata import table

    session = bind_completed_result(conn, request.run_id)
    cut = session.completed_cut_id
    if cut is None or (request.cut_id is not None and request.cut_id != cut):
        raise SemanticRefusal("dossier representation requires its exact completed cut")
    selected, origin = table("ops.task"), table("ops.task").alias("dossier_origin")
    result, membership = table("ops.task_result"), table("ops.cut_task")
    report = result.c.body["structural_product"]
    dossier = report["dossier"]
    representation = dossier["representation"]
    metadata = (
        conn.execute(
            select(
                origin.c.id.label("origin_id"),
                (
                    "structural:"
                    + func.encode(
                        func.sha256(
                            func.convert_to(
                                func.data.canonical_json(report.op("-")("retrieval_report")), "UTF8"
                            )
                        ),
                        "hex",
                    )
                ).label("product_id"),
                representation["policy"].astext.label("policy"),
                representation["membership_digest"].astext.label("membership_digest"),
                representation["facet_digest"].astext.label("facet_digest"),
                representation["mandatory_overflow"].as_boolean().label("mandatory_overflow"),
                func.jsonb_array_length(representation["selected"]).label("selected_count"),
                func.jsonb_array_length(dossier["members"]).label("full_member_count"),
                func.jsonb_array_length(representation["omitted"]).label("omitted_member_count"),
                func.jsonb_array_length(representation["missing_facets"]).label(
                    "missing_facet_count"
                ),
            )
            .select_from(selected)
            .join(origin, origin.c.id == func.coalesce(selected.c.reused_task_id, selected.c.id))
            .join(result, result.c.task_id == origin.c.id)
            .join(
                membership, (membership.c.task_id == selected.c.id) & (membership.c.cut_id == cut)
            )
            .where(
                selected.c.run_id == request.run_id,
                selected.c.id == request.task_id,
                selected.c.release_id == session.prepared.release_id,
                origin.c.release_id == session.prepared.release_id,
                selected.c.status.in_(("done", "reused")),
                selected.c.unit_type == "run",
                report["kind"].astext == "dossier",
            )
        )
        .mappings()
        .one_or_none()
    )
    if metadata is None:
        raise SemanticRefusal("dossier task is outside the selected completed cut")
    binding = {
        key: metadata[key] for key in ("product_id", "membership_digest", "facet_digest", "policy")
    }
    offset = 0
    if request.continuation:
        if any(getattr(request.continuation, key) != value for key, value in binding.items()):
            raise SemanticRefusal(
                "dossier continuation differs from exact membership/facets/policy"
            )
        offset = request.continuation.offset
    if offset > metadata["selected_count"]:
        raise SemanticRefusal("dossier continuation is outside representation")
    end = min(offset + request.limit, metadata["selected_count"])
    continuation = (
        DossierContinuation(**binding, offset=end) if end < metadata["selected_count"] else None
    )
    base = dict(
        run_id=request.run_id,
        cut_id=cut,
        task_id=request.task_id,
        **binding,
        full_member_count=metadata["full_member_count"],
        omitted_member_count=metadata["omitted_member_count"],
        missing_facet_count=metadata["missing_facet_count"],
        mandatory_overflow=metadata["mandatory_overflow"],
        continuation=continuation,
    )
    metadata_bytes = (
        len(
            canonical_bytes(
                {
                    key: value.model_dump(mode="json") if isinstance(value, BaseModel) else value
                    for key, value in base.items()
                }
            )
        )
        + 256
    )
    parameters = dict(origin_id=metadata["origin_id"], offset=offset, end_offset=end)
    size = conn.scalar(
        text(_DOSSIER_SLICE_SQL.replace("{projection}", "octet_length(body::text)")), parameters
    )
    if size is None or size + metadata_bytes > request.max_bytes:
        raise SemanticRefusal("dossier representation exceeds byte budget; narrow the member page")
    payload = conn.scalar(text(_DOSSIER_SLICE_SQL.replace("{projection}", "body")), parameters)
    if not isinstance(payload, dict):
        raise SemanticRefusal("dossier representation payload is unavailable")
    page = DossierRepresentationPage.model_validate({**base, **payload})
    if len(canonical_bytes(page.model_dump(mode="json"))) > request.max_bytes:
        raise SemanticRefusal("dossier representation response exceeds byte budget")
    return page
