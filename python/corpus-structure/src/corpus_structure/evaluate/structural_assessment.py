"""Independent multi-source group frames; no single-source unit is repurposed."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import Field, JsonValue, model_validator
from sqlalchemy import Connection, text

from corpus_structure.semantic.identity import canonical_bytes
from corpus_structure.semantic.structural_products import (
    StructuralInput,
    StructuralProductReport,
    StructuralValue,
)


class StructuralEvaluationFrame(StructuralValue):
    protocol: Literal["structural-evaluation-frame-1"] = "structural-evaluation-frame-1"
    inputs: StructuralInput
    operation: Literal["definition_applicability", "qualified_comparison", "dossier"]
    direction: Literal["source_first", "output_first"]
    rubric_version: str = Field(min_length=1)
    rubric_text: str = Field(min_length=1)
    product_ids: tuple[str, ...] = ()
    partition: Literal["development"] = "development"

    @model_validator(mode="after")
    def selection(self):
        if bool(self.product_ids) != (self.direction == "output_first"):
            raise ValueError("only output-first frames require frozen product identities")
        if len(set(self.product_ids)) != len(self.product_ids):
            raise ValueError("frame repeats a product identity")
        return self


class StructuralReferenceCase(StructuralValue):
    case_id: str = Field(min_length=1)
    facet: Literal[
        "applicability",
        "scope",
        "difference",
        "membership",
        "source_support",
        "completeness",
        "public_statement",
    ]
    path: tuple[str | int, ...] = Field(min_length=1)
    expected: JsonValue
    source_passages: tuple[str, ...] = Field(min_length=1)
    judgment: Literal["supported", "unsupported", "ambiguous", "unassessed"]
    explanation: str = Field(min_length=1)

    @model_validator(mode="after")
    def closure(self):
        if any((isinstance(p, int) and p < 0) or p == "" for p in self.path):
            raise ValueError("case path requires nonnegative indices and nonempty keys")
        if len(set(self.source_passages)) != len(self.source_passages):
            raise ValueError("case repeats a source passage")
        return self


class StructuralAuthoredReference(StructuralValue):
    protocol: Literal["structural-reference-1"] = "structural-reference-1"
    frame_digest: str = Field(pattern=r"^[a-f0-9]{64}$")
    cases: tuple[StructuralReferenceCase, ...] = Field(min_length=1)

    @model_validator(mode="after")
    def distinct(self):
        if len({c.case_id for c in self.cases}) != len(self.cases):
            raise ValueError("reference repeats case identity")
        return self


def create_structural_reference_set(
    conn: Connection,
    *,
    project_id: str,
    release_id: str,
    frame: StructuralEvaluationFrame,
) -> int:
    return conn.execute(
        text(
            "SELECT eval.create_structural_reference_set(:project,:release,CAST(:frame AS jsonb))"
        ),
        {
            "project": project_id,
            "release": release_id,
            "frame": canonical_bytes(frame.model_dump(mode="json", exclude_none=True)).decode(),
        },
    ).scalar_one()


def record_structural_reference_pass(
    conn: Connection,
    *,
    set_id: int,
    pass_kind: Literal["A", "B", "C"],
    actor: str,
    authored: bytes,
    parents: tuple[int, ...] = (),
) -> int:
    StructuralAuthoredReference.model_validate_json(authored)
    return conn.execute(
        text(
            "SELECT eval.record_structural_reference_pass("
            ":set,:kind,:actor,:authored,CAST(:parents AS jsonb))"
        ),
        {
            "set": set_id,
            "kind": pass_kind,
            "actor": actor,
            "authored": authored,
            "parents": canonical_bytes(list(parents)).decode(),
        },
    ).scalar_one()


def score_structural_reference(
    frame: StructuralEvaluationFrame,
    reference: StructuralAuthoredReference,
    product: dict[str, Any],
) -> dict[str, Any]:
    """Compare independently authored expectations; matching is not public admission."""
    if reference.frame_digest != frame.identity:
        raise ValueError("reference differs from frozen group frame")
    report = StructuralProductReport.model_validate(product)
    if report.inputs != frame.inputs or report.kind != frame.operation:
        raise ValueError("product differs from frozen group inputs or operation")
    if frame.direction == "output_first" and report.product_id not in frame.product_ids:
        raise ValueError("product is outside frozen output-first membership")
    passage_ids = {p.passage_id for p in frame.inputs.passages}
    cases = []
    for case in reference.cases:
        if not set(case.source_passages) <= passage_ids:
            raise ValueError("reference cites outside frozen source group")
        if case.facet == "public_statement":
            from corpus_structure.semantic.structural_admission import structural_statement

            actual: Any = {"public_statement": structural_statement(report)}
        else:
            actual = product
        found = True
        for step in case.path:
            if isinstance(actual, dict) and isinstance(step, str) and step in actual:
                actual = actual.get(step)
            elif isinstance(actual, list) and isinstance(step, int) and 0 <= step < len(actual):
                actual = actual[step]
            else:
                found = False
                actual = None
                break
        cases.append(
            dict(
                case_id=case.case_id,
                facet=case.facet,
                judgment=case.judgment,
                outcome="unassessed"
                if case.judgment == "unassessed"
                else (
                    "match"
                    if found and canonical_bytes(actual) == canonical_bytes(case.expected)
                    else "mismatch"
                ),
                found=found,
                expected=case.expected,
                actual=actual,
                source_passages=list(case.source_passages),
                explanation=case.explanation,
            )
        )
    return dict(
        protocol="structural-reference-comparison-1",
        frame_digest=frame.identity,
        cases=cases,
        quality_claim="declared_cases_only",
        publication_authority=False,
    )
