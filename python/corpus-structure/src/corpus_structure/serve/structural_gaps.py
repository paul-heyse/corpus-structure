"""Bounded gap reports over exact selected producers and authorized support."""

from hashlib import sha256
from typing import Any, Literal

from pydantic import Field, model_validator

from .selected_structural import (
    SelectedStructuralRoot,
    StructuralReadRequest,
    bounded_result,
    selected_contextual,
    selected_root,
    structural_report,
    structural_scope,
)
from .selected_structural import (
    producer as selected_producer,
)


class SelectedGapRequest(StructuralReadRequest):
    report: Literal[
        "unresolved_binding", "unknown_applicability_premise", "unconnected_supported_comparison"
    ]
    root: SelectedStructuralRoot
    binding: SelectedStructuralRoot | None = None
    admission: SelectedStructuralRoot | None = None
    occurrence_id: str | None = Field(default=None, min_length=1)
    scope: str | None = Field(default=None, min_length=1)
    limit: int = Field(default=20, strict=True, ge=1, le=100)
    cursor: str | None = Field(default=None, max_length=32768)

    @model_validator(mode="after")
    def selectors(self):
        if (
            self.binding is not None or self.admission is not None
        ) and self.report != "unconnected_supported_comparison":
            raise ValueError("binding and admission roots require the comparison gap")
        if self.occurrence_id is not None and self.report != "unresolved_binding":
            raise ValueError("occurrence selector requires the binding gap")
        return self


def selected_gap_rows(request, body) -> list[dict[str, Any]]:
    """Only recorded judgments yield gaps. Missing information remains unavailable."""
    if request.report == "unresolved_binding":
        candidates, decision = body["candidate_list"], body["relationship_decision"]
        if request.occurrence_id not in (None, candidates["occurrence_id"]):
            raise ValueError("occurrence is outside the exact selected decision")
        if request.scope not in (None, decision["scope"]):
            raise ValueError("scope is outside the exact selected decision")
        if (
            decision["candidate_list_id"] != candidates["list_id"]
            or decision["occurrence_id"] != candidates["occurrence_id"]
        ):
            raise ValueError("relationship decision differs from its exact candidate list")
        if decision["outcome"] == "selected":
            return []
        return [
            dict(
                status="actionable",
                reason=decision.get("reason") or "unresolved_relationship_decision",
                operation="relationship_selection",
                outcome=decision["outcome"],
                evidence=dict(
                    source_pin=body["source_pin"],
                    anchors=body["anchors"],
                    candidate_list=candidates,
                    relationship_decision=decision,
                ),
            )
        ]
    if request.scope not in (None, body["inputs"]["scope"]):
        raise ValueError("scope is outside the exact selected structural inputs")
    if request.report == "unconnected_supported_comparison":
        if body.get("comparison") is None:
            raise ValueError("comparison gap requires its actual comparison product")
        # Computational custody is not an independently admitted scientific witness.
        # Until an explicit authorized assertion is selected, no absent binding is a gap.
        return [
            dict(
                status="unavailable",
                reason="authorized_comparison_support_unavailable",
                operation="qualified_comparison",
                outcome="not_assessed",
                evidence=dict(comparison=body["comparison"], scientific_support="not-established"),
            )
        ]
    definition = body.get("definition")
    if definition is None:
        raise ValueError("applicability gap requires its actual applicability product")
    passages = {passage["passage_id"]: passage for passage in body["inputs"]["passages"]}
    return [
        dict(
            status="actionable",
            reason=premise["reason"],
            operation="definition_applicability",
            outcome=reading["outcome"],
            evidence=dict(
                dimension=premise["dimension"],
                state=premise["state"],
                usage=passages[definition["usage_id"]],
                cited_passages=[passages[key] for key in premise["evidence"]],
                component_ref=reading["component_ref"],
                relationship_ref=reading["link_ref"],
            ),
        )
        for reading in definition["readings"]
        for premise in reading["premises"]
        if premise["state"] in {"unknown", "incompatible"}
    ]


def inspect_selected_gap(conn, request: SelectedGapRequest):
    from corpus_structure.semantic.data_operation_json import json_bytes
    from corpus_structure.semantic.demand_queries import _cursor

    from .rich_queries import decode_rich_cursor

    selection = request.model_dump(
        mode="python",
        exclude={"cursor", "limit", "max_bytes", "read_id", "expected_cut", "implementation"},
    )
    cursor = None if request.cursor is None else decode_rich_cursor(request.cursor)
    if cursor is not None:
        if (
            set(cursor) != {"version", "selection", "read_id", "cut_id", "implementation", "after"}
            or cursor["version"] != "selected-structural-gap-v1"
            or cursor["selection"] != selection
        ):
            raise ValueError("gap continuation differs from exact selected report and scope")
        if request.read_id is not None and (
            request.read_id != cursor["read_id"] or request.expected_cut != cursor["cut_id"]
        ):
            raise ValueError("gap continuation differs from requested native read")
        if (
            request.implementation is not None
            and request.implementation != cursor["implementation"]
        ):
            raise ValueError("gap continuation differs from requested implementation")
        request = request.model_copy(
            update=dict(
                read_id=cursor["read_id"],
                expected_cut=cursor["cut_id"],
                implementation=cursor["implementation"],
            )
        )
    roots = tuple(
        root for root in (request.root, request.binding, request.admission) if root is not None
    )
    with structural_scope(conn, request, roots=roots) as acquired:
        selected = selected_root(acquired, request.root)
        if selected is None:
            return bounded_result(
                request,
                dict(
                    format="selected-structural-gap-v1",
                    availability="outside_selection",
                    cut_id=acquired.cut.identity,
                    cut=acquired.cut.record,
                    implementation=acquired.implementation,
                    rows=[],
                ),
            )
        binding_producer = admission_producer = None
        if request.report == "unresolved_binding":
            body = selected_contextual(acquired, selected)
            rows = selected_gap_rows(request, body)
        else:
            report = structural_report(acquired, selected)
            body = report.model_dump(mode="python", exclude_none=True)
            if (
                request.report == "unconnected_supported_comparison"
                and request.admission is not None
            ):
                from .selected_structural_admission import (
                    selected_structural_admission,
                    supported_comparison_gap_rows,
                )

                admission = selected_structural_admission(
                    acquired, request.admission, selected, report
                )
                binding_selected = (
                    None if request.binding is None else selected_root(acquired, request.binding)
                )
                binding_report = (
                    None
                    if binding_selected is None
                    else structural_report(acquired, binding_selected)
                )
                binding_producer = (
                    None if binding_selected is None else selected_producer(binding_selected)
                )
                admission_producer = (
                    None if admission is None else admission[1].model_dump(mode="python")
                )
                rows = supported_comparison_gap_rows(request, report, admission, binding_report)
            else:
                rows = selected_gap_rows(request, body)
        for row in rows:
            row["row_id"] = sha256(json_bytes(row)).hexdigest()
        rows.sort(key=lambda row: row["row_id"])
        after = None if cursor is None else cursor["after"]
        if after is not None and after not in {row["row_id"] for row in rows}:
            raise ValueError("gap continuation is outside exact selected judgments")
        remaining = [row for row in rows if after is None or row["row_id"] > after]
        chosen = remaining[: request.limit]
        next_cursor = (
            None
            if len(remaining) <= request.limit
            else _cursor(
                dict(
                    version="selected-structural-gap-v1",
                    selection=selection,
                    read_id=acquired.cut.record["read_id"],
                    cut_id=acquired.cut.identity,
                    implementation=acquired.implementation,
                    after=chosen[-1]["row_id"],
                )
            )
        )
        statuses = {row["status"] for row in rows}
        return bounded_result(
            request,
            dict(
                format="selected-structural-gap-v1",
                availability="unavailable"
                if statuses == {"unavailable"}
                else "observed"
                if rows
                else "inspected_empty",
                status="empty"
                if not statuses
                else next(iter(statuses))
                if len(statuses) == 1
                else "mixed",
                cut_id=acquired.cut.identity,
                cut=acquired.cut.record,
                implementation=acquired.implementation,
                report=request.report,
                producer=selected_producer(selected),
                rows=chosen,
                next_cursor=next_cursor,
                binding_producer=binding_producer,
                admission_producer=admission_producer,
                standing="private_proposal",
                public_admission="not-established",
            ),
        )
