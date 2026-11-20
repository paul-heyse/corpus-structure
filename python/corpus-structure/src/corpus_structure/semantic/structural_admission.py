"""Finite public structural statements, separate from retained producer reports.

Only native eligibility supplies admission witnesses. Canonical projection is not
an assessment and never elevates a producer's supplied member qualifications.
"""

from __future__ import annotations

from collections.abc import Mapping
from hashlib import sha256
from typing import Any

from .identity import canonical_bytes
from .refusal_types import SemanticRefusal
from .structural_products import DeclaredStructuralProductReport

POLICIES = {
    "definition_applicability": "independent-witnessed-applicability-1",
    "definition_components": "independent-definition-component-1",
    "qualified_comparison": "independent-structural-comparison-1",
    "dossier": "independent-structural-dossier-1",
    "condition_qualification": "independent-condition-qualification-1",
}


def structural_statement(
    report: DeclaredStructuralProductReport,
    component_id: str | None = None,
) -> dict[str, Any]:
    """Project complete meaning with exact current source citations."""
    if report.kind not in POLICIES:
        raise SemanticRefusal(f"No public structural policy for private {report.kind} reports")
    refs = {s.identity: s.model_dump(mode="json", exclude_none=True) for s in report.inputs.sources}
    passages = {p.passage_id: p for p in report.inputs.passages}

    def citation(identifier: str):
        passage = passages[identifier]
        source = refs[passage.source_ref]
        return {
            "source": source,
            **passage.model_dump(
                mode="json", exclude_none=True, exclude={"passage_id", "source_ref"}
            ),
        }

    def citations(values):
        resolved = {canonical_bytes(citation(value)): citation(value) for value in values}
        return [resolved[key] for key in sorted(resolved)]

    statement: dict[str, Any] = {
        "version": "structural-public-statement-3",
        "kind": report.kind,
        "scope": report.inputs.scope,
        "inventory_id": report.inputs.inventory_id,
        "input_policy_id": report.inputs.policy_id,
        "coverage_limits": sorted(report.inputs.coverage_limits),
        "exclusions": sorted(
            (
                {"left": citation(e.left), "right": citation(e.right)}
                for e in report.inputs.exclusions
            ),
            key=canonical_bytes,
        ),
    }

    if report.kind in {
        "definition_components",
        "definition_applicability",
        "condition_qualification",
    }:
        statement.pop("inventory_id")
        statement.pop("input_policy_id")

    def span_citation(span):
        value = citation(span.passage_id)
        value.update(start=span.start, end=span.end, text=span.text)
        return value

    def dossier_source_evidence(member):
        # Native task/contribution aliases belong to private custody. Public assembly
        # meaning retains the physical endpoints and their source-qualified region.
        endpoints = {
            canonical_bytes(value): value
            for c in (member.contribution_citations or ())
            for value in [dict(source_pointer=c.source_pointer, passage=span_citation(c.span))]
        }
        ordered = [endpoints[key] for key in sorted(endpoints)]
        physical_sources = {
            sha256(canonical_bytes(value["passage"]["source"])).hexdigest() for value in ordered
        }
        region = member.scope.split(":", 1)[-1]
        return ",".join(sorted(physical_sources)) + ":" + region, ordered

    if report.definition_components is not None:
        if component_id is None:
            raise ValueError("definition publication requires one exact component selector")
        selected = [
            c for c in report.definition_components.components if c.component_id == component_id
        ]
        if len(selected) != 1:
            raise ValueError("selected definition component is missing or duplicated")
        component = selected[0]
        statement["definition_component"] = {
            "term": span_citation(component.term),
            "content": span_citation(component.content),
            "interpretation": component.interpretation,
            "scope": component.scope,
            **(
                {"effective_version": component.effective_version}
                if component.effective_version is not None
                else {}
            ),
        }
    elif component_id is not None:
        raise ValueError("component selector requires a definition component report")
    if report.definition is not None:
        value = report.definition
        statement["definition"] = {
            "usage": citation(value.usage_id),
            "readings": sorted(
                (
                    {
                        "component": {
                            "term": span_citation(r.component.term),
                            "content": span_citation(r.component.content),
                            "interpretation": r.component.interpretation,
                            "scope": r.component.scope,
                            **(
                                {"effective_version": r.component.effective_version}
                                if r.component.effective_version is not None
                                else {}
                            ),
                        },
                        "outcome": r.outcome,
                        "evidence": citations(set(r.evidence)),
                        "premises": [
                            {
                                "dimension": p.dimension,
                                "state": p.state,
                                "evidence": citations(set(p.evidence)),
                            }
                            for p in r.premises
                        ],
                    }
                    for r in value.readings
                ),
                key=canonical_bytes,
            ),
        }
    if report.comparison is not None:
        value = report.comparison

        def member_statement(member):
            projected = {
                "dimension": member.dimension,
                "lexical_value": member.lexical_value,
                "evidence": citations(member.evidence),
            }
            if member.span is not None:
                projected["span"] = span_citation(member.span)
            if member.spans is not None:
                projected["spans"] = [span_citation(span) for span in member.spans]
            if member.literal is not None:
                projected["literal"] = member.literal.model_dump(mode="json", exclude_none=True)
            if member.condition is not None:
                projected["condition"] = member.condition
            if member.typed is not None:
                projected["typed"] = {
                    **member.typed.model_dump(
                        mode="json", exclude_none=True, exclude={"span", "basis_evidence"}
                    ),
                    "span": span_citation(member.typed.span),
                }
                if member.typed.basis_evidence:
                    projected["typed"]["basis_evidence"] = span_citation(
                        member.typed.basis_evidence
                    )
            return projected

        dimensions = []
        for dimension in value.dimensions:
            item: dict[str, Any] = {"dimension": dimension.dimension, "outcome": dimension.outcome}
            item.update(
                typed_outcome=dimension.typed_outcome, assumptions=list(dimension.assumptions)
            )
            if dimension.grouping_outcome is not None:
                item["grouping_outcome"] = dimension.grouping_outcome
            if dimension.member_comparisons is not None:
                item["member_comparisons"] = [
                    member.model_dump(mode="json") for member in dimension.member_comparisons
                ]
            for interval_name in ("removed_interval", "added_interval"):
                interval = getattr(dimension, interval_name)
                if interval is not None:
                    item[interval_name] = interval.model_dump(mode="json", exclude_none=True)
            for name in ("left", "right"):
                side = getattr(dimension, name)
                if side is not None:
                    item[name] = member_statement(side)
                group = getattr(dimension, f"{name}_group")
                if group is not None:
                    item[f"{name}_group"] = {
                        "state": group.state,
                        **({"grouping": group.grouping} if group.grouping else {}),
                        "members": [member_statement(member) for member in group.members],
                        "witnesses": [span_citation(span) for span in group.witnesses],
                    }
            dimensions.append(item)
        statement["comparison"] = {
            "left": citation(value.left_id),
            "right": citation(value.right_id),
            "dimensions": dimensions,
            "equivalence": value.equivalence,
            "identity_standing": value.identity_standing,
            "applicability": value.applicability,
        }
        if value.succession:
            statement["comparison"]["succession"] = {
                "older": citation(value.succession.older_id),
                "newer": citation(value.succession.newer_id),
                "evidence": span_citation(value.succession.evidence),
                "older_evidence": span_citation(value.succession.older_evidence),
            }
    if report.dossier is not None:
        value = report.dossier
        statement["dossier"] = {
            "root": value.root_id,
            "members": sorted(
                (
                    {
                        "passage": span_citation(m.citation),
                        "role": m.role,
                        "sense": m.sense,
                        "scope": dossier_source_evidence(m)[0] if m.contribution_ref else m.scope,
                        **(
                            {"effective_version": m.effective_version}
                            if m.effective_version is not None
                            else {}
                        ),
                        "qualification": m.qualification,
                        **(
                            {"definition_interpretation": m.definition_interpretation}
                            if m.definition_interpretation is not None
                            else {}
                        ),
                        **(
                            {"applicability_outcome": m.applicability_outcome}
                            if m.applicability_outcome is not None
                            else {}
                        ),
                        **(
                            dict(
                                endpoint_citations=dossier_source_evidence(m)[1],
                            )
                            if m.contribution_ref is not None
                            else {}
                        ),
                    }
                    for m in value.members
                ),
                key=canonical_bytes,
            ),
            "missing_sections": sorted(value.missing_sections),
            "membership_completeness": value.membership_completeness,
            "admission_scope": "membership_assembly_not_member_truth",
        }
    if value := report.condition_qualification:
        statement["condition_qualification"] = {
            "relation": value.relation,
            **({"effective_version": value.effective_version} if value.effective_version else {}),
            **{
                role: [
                    {"source_pointer": item.source_pointer, "passage": span_citation(item.span)}
                    for item in citations
                ]
                for role, citations in (
                    ("qualifier", value.qualifier),
                    ("host_predicate", value.host_predicate),
                )
            },
        }
    return statement


def structural_claim_id(statement: Mapping[str, Any]) -> str:
    return "structural-claim:" + sha256(canonical_bytes(statement)).hexdigest()
