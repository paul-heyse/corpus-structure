"""Bounded native source-operation progress; logs never supply missing native identity."""

from __future__ import annotations

import base64
from datetime import UTC, datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import text

from corpus_structure.semantic.characterization_store import (
    CharacterizationProductSummary,
    FamilyOutcomeSummary,
    HistoricalProviderSummary,
    read_inventory,
)
from corpus_structure.semantic.product_reference import ProductReference

from .source_lineage import SourceOperationLink


class NativeActivity(BaseModel):
    model_config = ConfigDict(frozen=True)
    observed_at: datetime
    owner_availability: Literal["active", "inactive", "unknown"]
    physical_availability: Literal["unavailable"] = "unavailable"
    phase: None = None
    reason: str = (
        "Native task status and supervisor custody do not establish provider-lane activity."
    )
    last_observed: dict[str, Any] | None = None


class OperationRun(BaseModel):
    model_config = ConfigDict(frozen=True)
    run_id: int
    role: str
    region: int | None
    stages: tuple[str, ...]
    status: str
    source_ready: bool
    supervisor: Literal["active", "inactive", "unknown"]
    anchor_run_id: int | None = None


class OperationStage(BaseModel):
    model_config = ConfigDict(frozen=True)
    run_id: int
    region: int | None
    method: str
    stage: str
    status: str
    reason: str | None
    count: int
    task_ids: tuple[int, ...]
    task_ids_omitted: int


class SettledProduct(BaseModel):
    model_config = ConfigDict(frozen=True)
    reference: ProductReference
    kind: Literal["layer", "view"]
    selected_run_id: int
    producer_run_id: int | None
    region: int | None
    release_id: str
    method: str
    summary: CharacterizationProductSummary | None = None
    summary_availability: Literal["available", "unavailable"]


class OperationRegion(BaseModel):
    model_config = ConfigDict(frozen=True)
    index: int
    base_document: ProductReference
    source_only: bool
    document_region_count: int | None = None
    original_sources: tuple[dict[str, Any], ...]
    original_sources_omitted: int
    declared_methods: tuple[str, ...]
    views: tuple[ProductReference, ...] = ()
    readiness: Literal["enriched", "partial", "source_only", "unsettled", "unknown"]
    families: tuple[FamilyOutcomeSummary, ...] = ()
    coverage_metadata_complete: bool


class OperationProvider(BaseModel):
    model_config = ConfigDict(frozen=True)
    producing_run_id: int | None
    producing_task_id: int
    reference: ProductReference
    provenance: HistoricalProviderSummary
    standing: Literal["historical_native_product"] = "historical_native_product"
    live_activity: Literal["unknown"] = "unknown"


class SourceOperationProgress(BaseModel):
    model_config = ConfigDict(frozen=True)
    version: Literal[1] = 1
    selected_run_id: int
    selected_role: str
    project_id: str
    release_id: str
    realization_id: str
    operation_id: UUID | None
    association: Literal["native_operation", "historical_anchor"]
    anchor_run_id: int | None
    selected_policy: dict[str, Any] | None
    capture_run_id: int | None
    capture_readiness: Literal["source_ready", "incomplete", "terminal", "unknown"]
    capture_association: Literal["recorded", "unavailable"]
    region_count: int | None
    document_count: int | None
    run_count: int
    task_counts: dict[str, int]
    view_readiness: Literal["enriched", "partial", "source_only", "unsettled", "unknown"]
    runs: tuple[OperationRun, ...]
    stages: tuple[OperationStage, ...]
    regions: tuple[OperationRegion, ...]
    settled_products: tuple[SettledProduct, ...]
    final_views: tuple[ProductReference, ...]
    selected_input_views: tuple[ProductReference, ...]
    providers: tuple[OperationProvider, ...]
    provider_provenance_availability: Literal["partial", "unavailable"]
    provider_provenance_reason: str = (
        "Protected summaries expose retained native_runs; "
        "missing provider records do not establish absent execution."
    )
    activity: NativeActivity
    after_region: int
    region_limit: int
    next_region: int | None
    next_run: int | None
    continuation: str | None = None
    detail_omissions: tuple[str, ...] = ()

    def without_details(self):
        return self.model_copy(
            update=dict(
                runs=(),
                stages=(),
                regions=(),
                settled_products=(),
                providers=(),
                detail_omissions=(
                    *self.detail_omissions,
                    "operation detail: response byte limit; inspect native status pages",
                ),
            )
        )


class OperationProgressCursor(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    version: Literal[1] = 1
    selected_run_id: int = Field(strict=True, gt=0)
    scope_id: str
    after_region: int = Field(default=-1, strict=True, ge=-1)
    region_limit: int = Field(default=8, strict=True, ge=1, le=32)
    after_run: int = Field(default=0, strict=True, ge=0)
    product_run_id: int | None = Field(default=None, strict=True, gt=0)
    product_after: tuple[int, str] | None = None

    def encode(self):
        return base64.urlsafe_b64encode(self.model_dump_json().encode()).decode().rstrip("=")

    @classmethod
    def decode(cls, value):
        if not isinstance(value, str) or len(value) > 4096:
            raise ValueError("invalid operation progress cursor")
        try:
            return cls.model_validate_json(
                base64.b64decode(value + "=" * (-len(value) % 4), altchars=b"-_", validate=True)
            )
        except (ValueError, TypeError) as error:
            raise ValueError("invalid operation progress cursor") from error


def _thin_run_columns():
    # A demand can describe a whole book. Project only the small metadata needed here.
    return """r.id,r.project_id,r.release_id,r.input_realization_id,r.status,r.sealed,
      r.options - 'characterization_demand' AS options,
      r.options ? 'characterization_demand' AS has_demand"""


def _scope(row, link, anchor):
    params = dict(
        project=row["project_id"],
        release=row["release_id"],
        realization=row["input_realization_id"],
    )
    scope = (
        "r.project_id=:project AND r.release_id=:release AND r.input_realization_id=:realization"
    )
    if link is not None:
        scope += " AND r.options->'source_operation'->>'operation_id'=:operation"
        params["operation"] = str(link.operation_id)
    else:
        scope += (
            " AND (r.id=:anchor OR r.options->>'characterization_anchor'=CAST(:anchor AS text))"
        )
        params["anchor"] = anchor
    return scope, params


def _read_products(conn, run, omitted, *, after=None, limit=32):
    try:
        with conn.begin_nested():
            page = read_inventory(conn, int(run["id"]), after=after, limit=limit, max_bytes=262144)
    except Exception as error:
        # A status read cannot turn unreadable native metadata into an absent product.
        omitted.append(f"run {run['id']} products unavailable: {type(error).__name__}")
        return [], None
    if page["continuation"] is not None:
        omitted.append(
            f"run {run['id']} product inventory continues at {page['continuation']}; "
            "use exact run inventory"
        )
    products = []
    for value in page["products"]:
        summary = (
            CharacterizationProductSummary.model_validate(value["summary"])
            if value.get("summary") is not None
            else None
        )
        if summary is None:
            omitted.append(
                f"run {run['id']} inventory summary unavailable; "
                "forward native reader migration required"
            )
        products.append(
            SettledProduct(
                reference=ProductReference(**value["reference"]),
                kind=value["kind"],
                selected_run_id=run["id"],
                producer_run_id=value.get("producer_run_id"),
                region=run["options"].get("characterization_region"),
                release_id=value["release_id"],
                method=value["method"],
                summary=summary,
                summary_availability="available" if summary is not None else "unavailable",
            )
        )
    return products, page["continuation"]


def project_operation_progress(
    *,
    row,
    link,
    anchor,
    run_rows,
    run_count,
    task_counts,
    stage_rows,
    region_rows,
    region_count,
    document_count,
    products,
    selected_input_views,
    after_region,
    region_limit,
    next_region,
    next_run,
    omissions=(),
):
    """Pure projection over native metadata, with independent historical provenance."""
    runs = []
    for value in run_rows:
        options = value["options"]
        role = options.get("source_operation", {}).get("role", "primary")
        runs.append(
            OperationRun(
                run_id=value["id"],
                role=role,
                region=options.get("characterization_region"),
                stages=tuple(options.get("characterization_stage", ())),
                status=value["status"],
                source_ready=value["source_ready"],
                supervisor=value["supervisor"],
                anchor_run_id=anchor
                if value.get("has_demand")
                else options.get("characterization_anchor"),
            )
        )
    capture_ids = {value.run_id for value in runs if value.role == "capture"}
    declared_capture = (
        (link.capture_run_id or (row["id"] if link.role == "capture" else None))
        if link is not None
        else None
    )
    if declared_capture is not None:
        capture_ids.add(declared_capture)
    capture_id = next(iter(capture_ids)) if len(capture_ids) == 1 else None
    capture = next((value for value in runs if value.run_id == capture_id), None)
    capture_readiness = "unknown"
    if capture is not None:
        capture_readiness = (
            "source_ready"
            if capture.source_ready
            else "terminal"
            if capture.status in {"failed", "cancelled"}
            else "incomplete"
        )
    omitted = list(omissions)
    if len(capture_ids) > 1:
        omitted.append("conflicting actual capture associations; no capture was selected")
    providers = []
    seen_providers = set()
    for product in products:
        if product.summary is None:
            continue
        for provider in product.summary.providers:
            key = (product.reference, provider.provider, provider.configuration_digest)
            if key not in seen_providers:
                seen_providers.add(key)
                providers.append(
                    OperationProvider(
                        producing_run_id=product.producer_run_id,
                        producing_task_id=product.reference.task_id,
                        reference=product.reference,
                        provenance=provider,
                    )
                )
        if (
            product.summary.coverage_omitted
            or product.summary.providers_omitted
            or any(p.availability_omitted for p in product.summary.providers)
        ):
            omitted.append(
                f"product {product.reference.task_id}/{product.reference.product_key} "
                "metadata summary is partial"
            )
    regions = []
    document_regions = {}
    for value in region_rows:
        count = value.get("document_region_count")
        if count is None:
            count = (
                1
                if document_count == region_count
                else region_count
                if document_count == 1
                else None
            )
        document_regions[ProductReference(**value["base_document"])] = count
    for value in region_rows:
        index = value["index"]
        views = [p for p in products if p.region == index and p.kind == "view"]
        last = max(views, key=lambda p: p.selected_run_id, default=None)
        last_summary = last.summary if last is not None else None
        families = []
        selected = (
            [last]
            if last is not None
            else [p for p in products if p.region == index and p.kind == "layer"]
        )
        for product in selected:
            if product.summary is not None:
                for family in product.summary.coverage:
                    families.append(family)
        readiness = (
            last_summary.readiness
            if last_summary is not None
            else "unknown"
            if views
            else "unsettled"
        )
        regions.append(
            OperationRegion(
                index=index,
                base_document=ProductReference(**value["base_document"]),
                source_only=value["source_only"],
                document_region_count=document_regions.get(
                    ProductReference(**value["base_document"])
                ),
                original_sources=tuple(value["original_sources"]),
                original_sources_omitted=value["original_sources_omitted"],
                declared_methods=tuple(value["declared_methods"]),
                views=tuple(p.reference for p in views),
                readiness=readiness or "unknown",
                families=tuple(
                    sorted(
                        families,
                        key=lambda value: (value.family, value.outcome, value.availability),
                    )
                ),
                coverage_metadata_complete=last_summary is not None
                and not last_summary.coverage_omitted,
            )
        )
    final_products = [
        p
        for p in products
        if p.kind == "view"
        and (
            p.region == -1
            or (p.summary is not None and document_regions.get(p.summary.base_document) == 1)
        )
    ]
    latest_by_document = {}
    for product in sorted(final_products, key=lambda p: p.selected_run_id):
        if product.summary is not None:
            latest_by_document[product.summary.base_document] = product
    final_readiness = (
        "unknown"
        if anchor is None
        or omitted
        or any(p.kind == "view" and p.summary is None for p in products)
        else "unsettled"
    )
    if (
        document_count is not None
        and len(latest_by_document) == document_count
        and document_count > 0
    ):
        states = {p.summary.readiness for p in latest_by_document.values()}
        final_readiness = (
            "enriched"
            if states == {"enriched"}
            else "source_only"
            if states == {"source_only"}
            else "partial"
        )
    active = any(value.supervisor == "active" for value in runs)
    all_observed = len(run_rows) == run_count and not any(
        value.supervisor == "unknown" for value in runs
    )
    return SourceOperationProgress(
        selected_run_id=row["id"],
        selected_role=link.role if link is not None else "primary",
        project_id=row["project_id"],
        release_id=row["release_id"],
        realization_id=row["input_realization_id"],
        operation_id=link.operation_id if link is not None else None,
        association="native_operation" if link is not None else "historical_anchor",
        anchor_run_id=anchor,
        selected_policy=row["options"].get("physical_policy"),
        capture_run_id=capture_id,
        capture_readiness=capture_readiness,
        capture_association="recorded" if capture_id is not None else "unavailable",
        region_count=region_count,
        document_count=document_count,
        run_count=run_count,
        task_counts=dict(task_counts),
        view_readiness=final_readiness,
        runs=tuple(runs),
        stages=tuple(OperationStage.model_validate(value) for value in stage_rows),
        regions=tuple(regions),
        settled_products=tuple(products),
        final_views=tuple(p.reference for p in latest_by_document.values()),
        selected_input_views=tuple(selected_input_views),
        providers=tuple(providers),
        provider_provenance_availability="partial" if providers else "unavailable",
        activity=NativeActivity(
            observed_at=datetime.now(UTC),
            owner_availability="active" if active else "inactive" if all_observed else "unknown",
        ),
        after_region=after_region,
        region_limit=region_limit,
        next_region=next_region,
        next_run=next_run,
        detail_omissions=tuple(dict.fromkeys(omitted)),
    )


def read_source_operation_progress(
    conn, row, *, after_region=-1, region_limit=8, after_run=0, cursor=None
):
    from .commands import run_source_ready
    from .liveness import observe_supervisor

    if (
        type(after_region) is not int
        or after_region < -1
        or not 1 <= region_limit <= 32
        or type(after_run) is not int
        or after_run < 0
    ):
        raise ValueError("invalid operation progress page")
    options = row["options"]
    link = (
        SourceOperationLink.model_validate(options["source_operation"])
        if options.get("source_operation") is not None
        else None
    )
    has_demand = row.get("has_characterization_demand", "characterization_demand" in options)
    anchor = row["id"] if has_demand else options.get("characterization_anchor")
    if link is None and anchor is None:
        return None
    if anchor is not None and (type(anchor) is not int or anchor < 1):
        raise ValueError("invalid native characterization anchor")
    scope_id = str(link.operation_id) if link is not None else "anchor:" + str(anchor)
    if cursor is not None:
        cursor = OperationProgressCursor.decode(cursor) if isinstance(cursor, str) else cursor
        if cursor.selected_run_id != row["id"] or cursor.scope_id != scope_id:
            raise ValueError("operation progress cursor belongs to another native selection")
        after_region, region_limit, after_run = (
            cursor.after_region,
            cursor.region_limit,
            cursor.after_run,
        )
    scope, params = _scope(row, link, anchor)
    omissions = []
    if link is not None:
        anchors = list(
            conn.execute(
                text(
                    f"SELECT r.id FROM ops.run r WHERE {scope} "
                    "AND r.options ? 'characterization_demand' ORDER BY r.id LIMIT 2"
                ),
                params,
            ).scalars()
        )
        if len(anchors) > 1:
            raise ValueError("native source operation has multiple demand anchors")
        anchor = anchors[0] if anchors else None
    region_count = document_count = None
    region_rows = []
    next_region = None
    if anchor is not None:
        header = (
            conn.execute(
                text("""SELECT r.project_id,r.release_id,r.input_realization_id,
                        jsonb_array_length(r.options->'characterization_demand'->'requests') AS
            region_count,
                        (SELECT count(DISTINCT value->'base_document') FROM
            jsonb_array_elements(r.options->'characterization_demand'->'requests')) AS
            document_count
            FROM ops.run r WHERE r.id=:anchor AND r.options ? 'characterization_demand'"""),
                dict(anchor=anchor),
            )
            .mappings()
            .one()
        )
        if any(
            header[key] != row[key] for key in ("project_id", "release_id", "input_realization_id")
        ):
            raise ValueError("operation anchor differs from the selected native binding")
        region_count, document_count = header["region_count"], header["document_count"]
        region_rows = list(
            conn.execute(
                text("""SELECT ordinal-1 AS index,value->'base_document' AS base_document,
             coalesce((value->>'source_only')::boolean,false) AS source_only,
                          (SELECT count(*) FROM
             jsonb_array_elements(r.options->'characterization_demand'->'requests') other WHERE
             other->'base_document'=demand.value->'base_document') AS document_region_count,
                          coalesce((SELECT jsonb_agg(s.value ORDER BY s.ord) FROM
             jsonb_array_elements(demand.value->'selected_sources') WITH ORDINALITY s(value,ord)
             WHERE s.ord<=16),'[]') AS original_sources,
                          greatest(jsonb_array_length(demand.value->'selected_sources')-16,0) AS
             original_sources_omitted,
                          ARRAY(SELECT jsonb_object_keys(demand.value->'method_options') ORDER
             BY 1) AS declared_methods
                          FROM ops.run r CROSS JOIN LATERAL
             jsonb_array_elements(r.options->'characterization_demand'->'requests') WITH
             ORDINALITY demand(value,ordinal)
             WHERE r.id=:anchor AND ordinal-1>:after_region ORDER BY ordinal LIMIT :limit"""),
                dict(anchor=anchor, after_region=after_region, limit=region_limit + 1),
            ).mappings()
        )
        if len(region_rows) > region_limit:
            region_rows = region_rows[:region_limit]
            next_region = region_rows[-1]["index"]
    run_count = conn.scalar(text(f"SELECT count(*) FROM ops.run r WHERE {scope}"), params)
    if run_count < 1:
        raise ValueError("native operation identity differs from its selected run")
    task_counts = dict(
        conn.execute(
            text(
                "SELECT t.status,count(*) FROM ops.task t JOIN ops.run r ON r.id=t.run_id "
                f"WHERE {scope} GROUP BY t.status"
            ),
            params,
        ).all()
    )
    lower, upper = after_region, after_region + region_limit
    page_scope = (
        f"{scope} AND (NOT (r.options ? 'characterization_region') "
        "OR (r.options->>'characterization_region')::integer=-1 "
        "OR (r.options->>'characterization_region')::integer "
        "BETWEEN :region_start AND :region_end)"
    )
    page_params = {**params, "region_start": lower + 1, "region_end": upper, "after_run": after_run}
    run_rows = list(
        conn.execute(
            text(
                f"SELECT {_thin_run_columns()} FROM ops.run r WHERE {page_scope} "
                "AND r.id>:after_run ORDER BY r.id LIMIT 65"
            ),
            page_params,
        ).mappings()
    )
    next_run = run_rows[63]["id"] if len(run_rows) > 64 else None
    run_rows = [dict(value) for value in run_rows[:64]]
    if next_run is not None:
        omissions.append("operation run page continues; use next_run with the same region page")
    capture_id = (
        (link.capture_run_id or (row["id"] if link.role == "capture" else None))
        if link is not None
        else None
    )
    if capture_id is not None:
        capture = next((value for value in run_rows if value["id"] == capture_id), None)
        if capture is None:
            capture = (
                conn.execute(
                    text(
                        f"SELECT {_thin_run_columns()} FROM ops.run r "
                        f"WHERE {scope} AND r.id=:capture"
                    ),
                    {**params, "capture": capture_id},
                )
                .mappings()
                .one_or_none()
            )
            if capture is not None:
                run_rows.append(dict(capture))
        if (
            capture is None
            or capture["options"].get("source_operation", {}).get("role") != "capture"
        ):
            raise ValueError("recorded capture differs from native operation scope")
    selected_ids = [value["id"] for value in run_rows]
    for value in run_rows:
        value["source_ready"] = run_source_ready(conn, value["id"])
        try:
            active, _waiting = observe_supervisor(conn, value["id"])
            value["supervisor"] = "active" if active else "inactive"
        except Exception:
            value["supervisor"] = "unknown"
    stage_rows = []
    if selected_ids:
        groups = list(
            conn.execute(
                text("""WITH groups AS (
                      SELECT t.run_id,(r.options->>'characterization_region')::integer AS
           region,m.id AS method_id,m.name AS method,t.stage,t.status,t.reason,count(*) AS count
                      FROM ops.task t JOIN ops.run r ON r.id=t.run_id JOIN ops.method_config c
           ON c.id=t.method_config_id JOIN ops.method m ON m.id=c.method_id
                      WHERE t.run_id=ANY(:run_ids) GROUP BY
           t.run_id,r.options->>'characterization_region',m.id,m.name,t.stage,t.status,t.reason)
           SELECT g.*,count(*) OVER() AS group_count,
                          ARRAY(SELECT ti.id FROM ops.task ti JOIN ops.method_config ci ON
             ci.id=ti.method_config_id
                            WHERE ti.run_id=g.run_id AND ci.method_id=g.method_id AND
              ti.stage=g.stage AND ti.status=g.status
              AND ti.reason IS NOT DISTINCT FROM g.reason ORDER BY ti.id LIMIT 16) AS task_ids,
             greatest(g.count-16,0) AS task_ids_omitted
           FROM groups g ORDER BY run_id,method,stage,status,reason NULLS FIRST LIMIT 257"""),
                dict(run_ids=selected_ids),
            ).mappings()
        )
        if len(groups) > 256:
            omissions.append(f"stage groups truncated: {groups[0]['group_count'] - 256} omitted")
        stage_rows = [
            {key: value for key, value in group.items() if key not in {"group_count", "method_id"}}
            for group in groups[:256]
        ]
    products = []
    selected_input_views = [
        ProductReference(**pin) for pin in options.get("characterization_views", ())[:16]
    ]
    continuation = None

    def page_cursor(**updates):
        return OperationProgressCursor(
            selected_run_id=row["id"],
            scope_id=scope_id,
            after_region=after_region,
            region_limit=region_limit,
            **updates,
        ).encode()

    for value in run_rows:
        if value["options"].get("characterization_stage") and continuation is None:
            remaining = 64 - len(products)
            if remaining <= 0:
                continuation = page_cursor(after_run=value["id"] - 1)
                omissions.append("operation product detail page continues")
            else:
                product_after = (
                    cursor.product_after
                    if cursor is not None and cursor.product_run_id == value["id"]
                    else None
                )
                selected, product_next = _read_products(
                    conn, value, omissions, after=product_after, limit=min(32, remaining)
                )
                products.extend(selected)
                if product_next is not None:
                    continuation = page_cursor(
                        after_run=value["id"] - 1,
                        product_run_id=value["id"],
                        product_after=tuple(product_next),
                    )
        pins = value["options"].get("characterization_views", ())
        if len(pins) > 16:
            omissions.append(
                f"run {value['id']} selected input view detail truncated: {len(pins) - 16} omitted"
            )
        selected_input_views.extend(ProductReference(**pin) for pin in pins[:16])
    if anchor is None:
        omissions.append(
            "no frozen primary demand anchor; requested regional/final coverage is unknown"
        )
    if link is None:
        omissions.append(
            "historical anchor has no recorded enclosing operation/capture association"
        )
    if continuation is None:
        if next_run is not None:
            continuation = page_cursor(after_run=next_run)
        elif next_region is not None:
            continuation = OperationProgressCursor(
                selected_run_id=row["id"],
                scope_id=scope_id,
                after_region=next_region,
                region_limit=region_limit,
            ).encode()
    result = project_operation_progress(
        row=row,
        link=link,
        anchor=anchor,
        run_rows=run_rows,
        run_count=run_count,
        task_counts=task_counts,
        stage_rows=stage_rows,
        region_rows=region_rows,
        region_count=region_count,
        document_count=document_count,
        products=products,
        selected_input_views=tuple(dict.fromkeys(selected_input_views)),
        after_region=after_region,
        region_limit=region_limit,
        next_region=next_region,
        next_run=next_run,
        omissions=omissions,
    )
    result = result.model_copy(update={"continuation": continuation})
    if len(result.model_dump_json().encode()) > 1048576:
        result = result.without_details()
    return result
