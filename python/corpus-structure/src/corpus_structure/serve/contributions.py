"""Pinned, bounded inspection of contributions independently of complete records.

This surface grants no admission authority. Paging covers the selected retained
inventory, never original-source completeness or independent correctness.
"""

from __future__ import annotations

import base64
import json
from dataclasses import asdict
from hashlib import sha256
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, JsonValue, model_validator
from sqlalchemy import Connection, Text, func, select, tuple_

from corpus_structure.semantic.continuations import decode_continuation, validate_continuation
from corpus_structure.semantic.contribution_queries import read_source_contributions
from corpus_structure.semantic.identity import canonical_bytes
from corpus_structure.semantic.query import bind_completed_result
from corpus_structure.semantic.refusals import InvalidContinuation, SemanticRefusal
from corpus_structure.serve.journey import params_digest


class ContributionRequest(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    run_id: int = Field(strict=True, gt=0)
    source_view_id: int | None = Field(default=None, strict=True, gt=0)
    method: str | None = None
    operation_key: str | None = None
    operation_version: str | None = None
    contribution_id: str | None = None
    occurrence_id: str | None = Field(
        default=None,
        description=(
            "Own anchored SourceContribution physical occurrence identity; "
            "excludes anchorless products associated only through endpoints or members."
        ),
    )
    kind: Literal["occurrence", "proposal", "relation", "composite", "diagnostic"] | None = None
    include_details: bool = False
    include_interpretation: bool = False
    include_assessment: bool = False
    include_publication: bool = False
    include_support: bool = False
    cursor: str | None = None
    limit: int = Field(default=100, strict=True, ge=1, le=1000)
    max_bytes: int = Field(default=8_000_000, strict=True, ge=1, le=32_000_000)
    page_bytes: int = Field(default=1_000_000, strict=True, ge=1, le=32_000_000)

    def selection(self):
        return self.model_dump(exclude={"cursor", "limit", "max_bytes", "page_bytes"})

    @model_validator(mode="after")
    def supported_facets(self):
        if self.include_support and not self.include_publication:
            raise ValueError("local source support requires the publication facet")
        return self


class ContributionPage(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    version: Literal["contribution-inspection-3"] = "contribution-inspection-3"
    run_id: int
    cut_id: int
    binding: dict[str, JsonValue]
    selection: dict[str, JsonValue]
    items: tuple[dict[str, JsonValue], ...]
    inventory_counts: dict[str, int]
    population_paging_complete: bool
    next_cursor: str | None = None
    standing: Literal[
        "retained_private",
        "mixed_private_and_local_source_claims",
        "mixed_private_and_local_semantic_claims",
    ] = "retained_private"
    publication: Literal["not_included", "included"] = "not_included"
    interpretation: Literal["not_included", "included"] = "not_included"
    assessment: Literal["not_included", "included"] = "not_included"
    assessment_scope: Literal["published_admission_witnesses_only"] = (
        "published_admission_witnesses_only"
    )
    scientific_support: Literal["unmodeled"] = "unmodeled"
    source_coverage: Literal["not_established_by_contribution_inventory"] = (
        "not_established_by_contribution_inventory"
    )


def serve_contributions(conn: Connection, request: ContributionRequest) -> ContributionPage:
    return _contributions(conn, request, paginate=True)


def _contributions(
    conn: Connection, request: ContributionRequest, *, paginate: bool
) -> ContributionPage:
    session = bind_completed_result(conn, request.run_id)
    cut_id = session.completed_cut_id
    if cut_id is None:
        raise SemanticRefusal("contribution inspection requires a completed cut")
    query = params_digest(
        dict(version="contribution-inspection-3", cut=cut_id, selection=request.selection())
    )
    binding = session.binding
    expected = dict(
        release=binding.release_id,
        realization=binding.realization_id,
        revision=binding.data_revision,
        query=query,
    )
    offset = 0
    if request.cursor is not None:
        body = decode_continuation(request.cursor, kind="primitive")
        validate_continuation(session.prepared, body, expected)
        position = body.get("after")
        if not isinstance(position, str) or not position.isascii() or not position.isdecimal():
            raise InvalidContinuation("invalid contribution continuation position")
        offset = int(position)
    inventory = read_source_contributions(
        conn,
        prepared=session.prepared,
        run_id=request.run_id,
        cut_id=cut_id,
        source_view_id=request.source_view_id,
        method=request.method,
        operation_key=request.operation_key,
        operation_version=request.operation_version,
        contribution_id=request.contribution_id,
        occurrence_id=request.occurrence_id,
        kind=request.kind,
        limit=10_000,
        include_details=request.include_details,
        include_interpretation=request.include_interpretation,
        max_bytes=request.max_bytes,
    )
    if inventory.more:
        raise SemanticRefusal("contribution inventory exceeds 10000 rows; narrow the selection")
    local_rows = ()
    semantic_rows = ()
    if request.include_publication or request.include_assessment:
        from corpus_structure.semantic.local_admission import (
            LocalAssertionRow,
            local_assertion_facets,
            local_assertion_support,
        )
        from corpus_structure.semantic.local_semantic_admission import semantic_assertion_facets
        from corpus_structure.semantic.metadata import table

        if (
            request.include_publication
            and "LocalContributionPublicationPolicy" not in session.prepared.index.definitions
        ):
            raise SemanticRefusal("selected release does not support local publication facets")
        queries = []
        retained_bytes = sum(
            len(canonical_bytes(rows))
            for rows in (
                inventory.reports,
                inventory.operations,
                inventory.contributions,
                inventory.interpretations,
            )
        )
        transfer_total = retained_bytes + 1024
        count_total = 0
        for name, hidden in (
            ("local_assertion", {"anchors_json", "literal_pieces_json"}),
            ("local_semantic_assertion", {"statement_json", "anchors_json"}),
        ):
            if name == "local_assertion" and not request.include_publication:
                continue
            if (
                name == "local_semantic_assertion"
                and "LocalSemanticPublicationPolicy" not in session.prepared.index.definitions
            ):
                continue
            relation = table("data." + name)
            columns = tuple(
                column
                for column in relation.c
                if request.include_support or column.name not in hidden
            )
            query = (
                select(*columns)
                .where(
                    relation.c.release_id == binding.release_id,
                    relation.c.realization_id == binding.realization_id,
                    relation.c.cut_id == cut_id,
                    tuple_(
                        relation.c.selected_task_id,
                        relation.c.origin_task_id,
                        relation.c.contribution_id,
                    ).in_(
                        [
                            (row["selected_task_id"], row["origin_task_id"], row["contribution_id"])
                            for row in inventory.contributions
                        ]
                    ),
                )
                .order_by(relation.c.assertion_id)
                .limit(10_001)
            )
            column_bytes = sum(
                func.octet_length(func.coalesce(column.cast(Text), "")) for column in columns
            )
            count, transfer = conn.execute(
                query.with_only_columns(
                    func.count(), func.coalesce(func.sum(6 * column_bytes + 1536), 0)
                )
                .order_by(None)
                .limit(None)
            ).one()
            count_total += count
            transfer_total += transfer
            queries.append((name, query))
        if count_total > 10_000 or transfer_total > request.max_bytes:
            raise SemanticRefusal(
                "local witness population exceeds row/byte budget; narrow the selection"
            )
        for name, query in queries:
            decoded = []
            for row in conn.execute(query).mappings():
                values = {
                    str(key): value
                    for key, value in row.items()
                    if key not in {"release_id", "realization_id"}
                }
                if name == "local_semantic_assertion":
                    decoded.append(
                        semantic_assertion_facets(values, support=request.include_support)
                    )
                else:
                    decoded.append(
                        local_assertion_support(LocalAssertionRow(**values))
                        if request.include_support
                        else local_assertion_facets(values)
                    )
            if name == "local_semantic_assertion":
                semantic_rows = tuple(decoded)
            else:
                local_rows = tuple(decoded)
    interpretations = (
        tuple(
            {
                key: row[key]
                for key in (
                    "selected_task_id",
                    "origin_task_id",
                    "source_view_id",
                    "contribution_id",
                    "operation_key",
                    "occurrence_id",
                    "kind",
                    "semantic_type",
                    "disposition",
                    "standing",
                    "source_field_state",
                    "anchor_role",
                    "value",
                    "members",
                    "endpoints",
                    "computation_dependencies",
                    "reason",
                    "alternatives",
                )
                if key in row
            }
            for row in inventory.interpretations
        )
        if request.include_interpretation
        else ()
    )
    assessments = ()
    if request.include_assessment:
        assessment_fields = {
            "assertion_id",
            "claim_id",
            "selected_task_id",
            "origin_task_id",
            "contribution_id",
            "operation_key",
            "operation_version",
            "operation_question",
            "policy_id",
            "policy_version",
            "evaluation_id",
            "evaluation_digest",
            "unit_id",
            "pass_id",
            "frame_id",
            "case_id",
            "facet",
            "rubric_version",
            "context_policy",
        }
        assessment_rows = []
        witnesses_by_product = {}
        for row in semantic_rows:
            key = (row["selected_task_id"], row["origin_task_id"], row["contribution_id"])
            witnesses_by_product.setdefault(key, []).append(
                {field: value for field, value in row.items() if field in assessment_fields}
            )
        for contribution in inventory.contributions:
            witnesses = witnesses_by_product.get(
                (
                    contribution["selected_task_id"],
                    contribution["origin_task_id"],
                    contribution["contribution_id"],
                ),
                [],
            )
            assessment_rows.append(
                dict(
                    contribution_id=contribution["contribution_id"],
                    selected_task_id=contribution["selected_task_id"],
                    origin_task_id=contribution["origin_task_id"],
                    outcome="supported" if witnesses else "no_public_assessment",
                    basis="independently_adjudicated_exact_case"
                    if witnesses
                    else "no_published_admission_witness",
                    scope="published_admission_witnesses_only",
                    witnesses=witnesses,
                )
            )
        assessments = tuple(assessment_rows)
    items = tuple(
        dict(population=population, row=json.loads(canonical_bytes(row)))
        for population, rows in (
            ("report", inventory.reports),
            ("operation", inventory.operations),
            ("contribution", inventory.contributions),
            ("interpretation", interpretations),
            ("assessment", assessments),
            ("local_assertion", local_rows),
            ("local_semantic_assertion", semantic_rows if request.include_publication else ()),
        )
        for row in rows
    )
    if len(canonical_bytes(items)) > request.max_bytes:
        raise SemanticRefusal("contribution inventory exceeds its detached byte budget")
    if offset > len(items):
        raise InvalidContinuation("contribution continuation is outside its population")
    end = min(offset + request.limit, len(items)) if paginate else len(items)
    more = end < len(items)
    cursor = (
        base64.urlsafe_b64encode(canonical_bytes(dict(**expected, after=str(end)))).decode()
        if more
        else None
    )
    result = ContributionPage(
        run_id=request.run_id,
        cut_id=cut_id,
        binding=json.loads(canonical_bytes(asdict(binding))),
        selection=request.selection(),
        items=items[offset:end],
        inventory_counts=dict(
            reports=len(inventory.reports),
            operations=len(inventory.operations),
            contributions=len(inventory.contributions),
            interpretations=len(interpretations),
            assessments=len(assessments),
            local_assertion_witnesses=len(local_rows),
            admitted_source_claims=len({row["claim_id"] for row in local_rows}),
            local_semantic_assertion_witnesses=len(semantic_rows),
            admitted_semantic_claims=len({row["claim_id"] for row in semantic_rows}),
        ),
        publication="included" if request.include_publication else "not_included",
        interpretation="included" if request.include_interpretation else "not_included",
        assessment="included" if request.include_assessment else "not_included",
        standing="mixed_private_and_local_semantic_claims"
        if semantic_rows and request.include_publication
        else ("mixed_private_and_local_source_claims" if local_rows else "retained_private"),
        population_paging_complete=not more,
        next_cursor=cursor,
    )
    if paginate and len(result.model_dump_json().encode()) > request.page_bytes:
        raise SemanticRefusal(
            "contribution response exceeds page byte budget; narrow the selection"
        )
    return result


def export_contribution_selection(
    conn: Connection, request: ContributionRequest, destination: Path
) -> dict:
    """Atomic bounded selection export; a full detached review bundle is a separate scope."""
    if request.cursor is not None or request.include_details:
        raise ValueError(
            "selected export starts from the full selection and excludes raw report details"
        )
    if destination.exists():
        raise FileExistsError(destination)
    page = _contributions(conn, request, paginate=False)
    destination.parent.mkdir(parents=True, exist_ok=True)
    with TemporaryDirectory(prefix=".contribution-export-", dir=destination.parent) as temporary:
        root = Path(temporary) / "export"
        root.mkdir()
        content = b"".join(canonical_bytes(item) + b"\n" for item in page.items)
        manifest = dict(
            version="contribution-selection-export-1",
            binding=page.binding,
            run_id=page.run_id,
            cut_id=page.cut_id,
            selection=page.selection,
            inventory_counts=page.inventory_counts,
            standing=page.standing,
            assessment=page.assessment,
            assessment_scope=page.assessment_scope,
            source_coverage=page.source_coverage,
            scientific_support=page.scientific_support,
            population_complete=page.population_paging_complete,
            scope="bounded selected inventory; not a self-contained PCE09 review bundle",
            private_grades="excluded; existing protected evaluator owns private grades",
            file="items.jsonl",
            sha256=sha256(content).hexdigest(),
            bytes=len(content),
            items=len(page.items),
        )
        encoded_manifest = canonical_bytes(manifest) + b"\n"
        if len(content) + len(encoded_manifest) > request.max_bytes:
            raise SemanticRefusal(
                "contribution export exceeds total byte budget; narrow the selection"
            )
        (root / "items.jsonl").write_bytes(content)
        (root / "manifest.json").write_bytes(encoded_manifest)
        from corpus_structure.serve.companion_export import _publish_directory

        _publish_directory(root, destination)
    return manifest
