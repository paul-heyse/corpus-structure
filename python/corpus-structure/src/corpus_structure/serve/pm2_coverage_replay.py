"""Replay exact PM2 worklists using the detached bundle's retained custody."""

from collections.abc import Iterable, Mapping, Sequence
from typing import Any

from corpus_structure.semantic.observations import source_python
from corpus_structure.semantic.pm2_coverage import (
    ScopeIntent,
    ScopeSettlement,
    ScopeWorklist,
    derive_scope_coverage,
)
from corpus_structure.serve.contributions import ContributionRequest


def _verify_origin(
    intent: ScopeIntent, settlement: ScopeSettlement, origin: Mapping[str, Any]
) -> None:
    if (
        origin.get("input_hash") != settlement.input_hash
        or origin.get("unit_type") != settlement.unit_type
        or origin.get("origin_unit_id") != settlement.unit_id
        or (settlement.status != "reused" and origin.get("task_status") != settlement.status)
    ):
        raise ValueError("PM2 scope settlement differs from retained task metadata")
    body = origin.get("body") or {}
    operations = body.get("contribution_operations") or ()
    if operations:
        first = operations[0]
        if (
            first["question"],
            first["operation_version"],
            first["outcome"],
            first["inspected_count"],
            first["emitted_count"],
            first.get("reason"),
        ) != (
            settlement.question,
            settlement.operation_version,
            settlement.outcome,
            settlement.inspected,
            settlement.emitted,
            settlement.result_reason,
        ):
            raise ValueError("PM2 scope differs from retained operation settlement")
    elif settlement.outcome is not None:
        raise ValueError("PM2 scope operation has no retained result")

    detail = body.get("parse_detail")
    native = (source_python(detail) or {}).get("pm2_native") if detail is not None else None
    if native is not None:
        pieces = native["source_map"]["context_pieces"]
        if (
            native["input_digest"] != intent.input_digest
            or len(pieces) != 1
            or pieces[0]["source_view_id"] != intent.source_view_id
            or (pieces[0]["start"], pieces[0]["end"]) != intent.extent
        ):
            raise ValueError("PM2 scope extent differs from the retained native source map")
        if (
            intent.operation_version == "3"
            and settlement.provider_outcome != native["native"]["outcome"]
        ):
            raise ValueError("PM2 provider outcome differs from its retained native report")
    elif settlement.outcome is not None:
        raise ValueError("PM2 scope operation lacks its retained native source map")


def verify_scope_worklists(
    selections: Sequence[ContributionRequest],
    scopes: Mapping[int, dict[str, Any]],
    coverage: Mapping[int, list[dict[str, Any]]],
    reports: Mapping[tuple[int, int, int], dict[str, Any]],
    worklists: Iterable[dict[str, Any]],
    sources: Iterable[dict[str, Any]],
    origins: Iterable[dict[str, Any]],
) -> None:
    """Check derivation and retained references; manifest binding authenticates completeness."""
    expected = {index for index, request in enumerate(selections) if request.include_scope_coverage}
    seen: set[int] = set()
    extent_by_source: dict[int, int] = {}
    origin_checks: dict[int, list[tuple[ScopeIntent, ScopeSettlement]]] = {}
    for proof in worklists:
        index = proof.get("selection_index")
        if (
            type(index) is not int
            or index not in expected - seen
            or set(proof) != {"selection_index", "run_id", "cut_id", "release_id", "worklist"}
        ):
            raise ValueError("review has an unexpected or repeated PM2 worklist")
        seen.add(index)
        scope = scopes.get(index)
        if scope is None or (proof["run_id"], proof["cut_id"], proof["release_id"]) != (
            scope["run_id"],
            scope["cut_id"],
            scope["binding"]["release_id"],
        ):
            raise ValueError("PM2 worklist differs from the selected run, cut or release")
        request = selections[index]
        evidence = ScopeWorklist.model_validate(proof["worklist"])
        derived = derive_scope_coverage(evidence, completed=True)
        if evidence.select(request.source_view_id, request.selected_task_id) != evidence:
            raise ValueError("PM2 worklist is outside its selected source view or task")
        rows = [
            item.model_dump(mode="json")
            for item in derived
            if request.selected_task_id is None or item.task_id == request.selected_task_id
        ]
        if rows != coverage.get(index, []) or scope["inventory_counts"].get(
            "scope_coverage"
        ) != len(rows):
            raise ValueError("review PM2 coverage differs from worklist replay")
        by_digest = {item.input_digest: item for item in evidence.intents}
        for intent in evidence.intents:
            extent_by_source[intent.source_view_id] = max(
                extent_by_source.get(intent.source_view_id, 0), intent.extent[1]
            )
        for settlement in evidence.settlements:
            intent = settlement.split_scope or by_digest[settlement.input_hash]
            extent_by_source[intent.source_view_id] = max(
                extent_by_source.get(intent.source_view_id, 0), intent.extent[1]
            )
            origin = settlement.reused_task_id or settlement.id
            origin_checks.setdefault(origin, []).append((intent, settlement))
            if request.selected_task_id is not None and settlement.id != request.selected_task_id:
                continue  # A split ancestor authenticates the child but is not displayed.
            report = reports.get((index, settlement.id, origin))
            if report is None or (
                report["source_view_id"],
                report["task_status"],
                report["cut_member"],
            ) != (settlement.unit_id, settlement.status, settlement.cut_origin is not None):
                raise ValueError("PM2 task custody differs from the selected report population")

    if seen != expected:
        raise ValueError("review lacks its selected PM2 worklist")
    if extent_by_source:
        for source in sources:
            extent = extent_by_source.pop(source["source_view_id"], 0)
            if extent > len(source["text"]):
                raise ValueError("PM2 worklist extent is outside its retained source view")
        if extent_by_source:
            raise ValueError("PM2 worklist lacks its retained source view")
    if origin_checks:
        for origin in origins:
            for intent, settlement in origin_checks.pop(origin["origin_task_id"], ()):
                _verify_origin(intent, settlement, origin)
        if origin_checks:
            raise ValueError("PM2 worklist lacks its retained task metadata")
