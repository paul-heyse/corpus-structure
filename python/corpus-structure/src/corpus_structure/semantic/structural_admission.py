"""Finite public structural statements, separate from retained producer reports.

Only native eligibility supplies admission witnesses. Canonical projection is not
an assessment and never elevates a producer's supplied member qualifications.
"""

from __future__ import annotations

import json
from collections.abc import Mapping
from dataclasses import dataclass
from hashlib import sha256
from typing import Any

from .identity import canonical_bytes
from .refusals import SemanticRefusal
from .structural_products import StructuralProductReport

POLICIES = {
    "definition_applicability": "independent-witnessed-applicability-1",
    "definition_components": "independent-definition-component-1",
    "qualified_comparison": "independent-structural-comparison-1",
    "dossier": "independent-structural-dossier-1",
}


def structural_statement(
    report: StructuralProductReport, component_id: str | None = None
) -> dict[str, Any]:
    """Project complete meaning and physical citations, without derivation aliases."""
    if report.kind not in POLICIES:
        raise SemanticRefusal(f"No public structural policy for private {report.kind} reports")
    refs = {s.identity: s.model_dump(mode="json", exclude_none=True) for s in report.inputs.sources}
    passages = {p.passage_id: p for p in report.inputs.passages}

    def citation(identifier: str):
        passage = passages[identifier]
        source = {
            k: v
            for k, v in refs[passage.source_ref].items()
            if k
            not in {
                "run_id",
                "cut_id",
                "release_id",
                "result_revision",
                "source_view_id",
                "native_task_id",
            }
        }
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

    if report.kind in {"definition_components", "definition_applicability"}:
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
    return statement


def structural_claim_id(statement: Mapping[str, Any]) -> str:
    return "structural-claim:" + sha256(canonical_bytes(statement)).hexdigest()


@dataclass(frozen=True)
class StructuralAssertionRow:
    assertion_id: str
    claim_id: str
    selected_task_id: int
    origin_task_id: int
    cut_id: int
    product_id: str
    product_kind: str
    policy_id: str
    policy_version: str
    set_id: int
    c_pass_id: int
    c_content_digest: str
    frame_digest: str
    case_id: str
    statement_json: str
    sources_json: str


def load_structural_grade_evidence(conn, job: Mapping[str, Any], cut_id: int):
    from sqlalchemy import text

    dependencies = json.loads(job["dependencies"]) if job.get("dependencies") else {}
    if not dependencies.get("structural_admission"):
        return ()
    return tuple(
        conn.execute(
            text("SELECT data.structural_publication_candidates(:project,:release,:run,:cut)"),
            {
                "project": job["project_id"],
                "release": job["release_id"],
                "run": job["id"],
                "cut": cut_id,
            },
        ).scalar_one()
    )


def project_structural_assertions(prepared, evidence):
    if not evidence:
        return ()
    if "StructuralPublicationPolicy" not in prepared.index.definitions:
        raise ValueError("release does not admit structural publication")
    for row in evidence:
        prepared.validate_json("StructuralPublicStatement", row["statement_json"])
    return tuple(StructuralAssertionRow(**row) for row in evidence)


def structural_assertion_facets(row: Mapping[str, Any], *, support: bool = False):
    result = {
        key: value for key, value in row.items() if key not in {"statement_json", "sources_json"}
    }
    result.update(
        standing="admitted_structural_statement",
        scientific_truth="not_established",
        member_truth="not_established_by_assembly_admission",
    )
    if support:
        result.update(
            statement=json.loads(row["statement_json"]), sources=json.loads(row["sources_json"])
        )
    return result


def read_structural_assertions(
    conn,
    *,
    release_id: str,
    realization_id: str,
    product_ids: tuple[str, ...],
    support: bool = False,
    max_bytes: int = 1_000_000,
):
    """Read admitted standing from the same selected realization, never producer labels."""
    from sqlalchemy import select

    from .metadata import table

    if not product_ids:
        return ()
    assertions = table("data.structural_assertion")
    fields = tuple(
        name
        for name in StructuralAssertionRow.__dataclass_fields__
        if support or name not in {"statement_json", "sources_json"}
    )
    statement = (
        select(*(assertions.c[name] for name in fields))
        .where(
            assertions.c.release_id == release_id,
            assertions.c.realization_id == realization_id,
            assertions.c.product_id.in_(product_ids),
        )
        .order_by(assertions.c.assertion_id)
    )
    from .pdf_record_reader import PublishedReadBudget

    PublishedReadBudget(10_000, max_bytes).preflight(conn, statement)
    rows = conn.execute(statement).mappings()
    return tuple(structural_assertion_facets(row, support=support) for row in rows)
