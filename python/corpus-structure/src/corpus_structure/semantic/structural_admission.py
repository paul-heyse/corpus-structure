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
        return sorted((citation(v) for v in values), key=canonical_bytes)

    statement: dict[str, Any] = {
        "version": "structural-public-statement-2",
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
            "eligible_targets": sorted(value.eligible_targets),
            "candidate_targets": sorted(value.candidate_targets),
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
            "inventory_coverage": value.inventory_coverage,
            "retrieval_diagnosis": value.retrieval_diagnosis,
        }
    if report.comparison is not None:
        value = report.comparison
        dimensions = []
        for dimension in value.dimensions:
            item: dict[str, Any] = {"dimension": dimension.dimension, "outcome": dimension.outcome}
            for name in ("left", "right"):
                side = getattr(dimension, name)
                if side is not None:
                    item[name] = {
                        "dimension": side.dimension,
                        "lexical_value": side.lexical_value,
                        "evidence": citations(side.evidence),
                    }
            dimensions.append(item)
        statement["comparison"] = {
            "left": citation(value.left_id),
            "right": citation(value.right_id),
            "dimensions": dimensions,
            "equivalence": value.equivalence,
            "identity_standing": value.identity_standing,
        }
    if report.dossier is not None:
        value = report.dossier
        statement["dossier"] = {
            "root": value.root_id,
            "members": sorted(
                (
                    {
                        "passage": citation(m.passage_id),
                        "role": m.role,
                        "sense": m.sense,
                        "scope": m.scope,
                        **(
                            {"effective_version": m.effective_version}
                            if m.effective_version is not None
                            else {}
                        ),
                        "qualification": m.qualification,
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
