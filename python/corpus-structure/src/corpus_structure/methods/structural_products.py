"""Compose attributed structural readings; similarity never supplies semantic support.

The operation accepts source-supported upstream readings. Native custody and public
admission remain separate boundaries; these producers emit only private proposals.
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from typing import Self

from pydantic import ConfigDict, model_validator

from corpus_structure.core.method import Digest, Resources, UnitRef, UnitResult
from corpus_structure.core.vocab import MethodFamily, MethodTier, ObservationOutcome, TaskUnitType
from corpus_structure.semantic.structural_products import (
    DIMENSIONS,
    MANDATORY_ROLES,
    ClauseReading,
    ComparisonProduct,
    DefinitionProduct,
    DefinitionReading,
    DimensionComparison,
    DossierMember,
    DossierProduct,
    StructuralInput,
    StructuralProductReport,
    StructuralValue,
)


def definition_applicability(
    inputs: StructuralInput,
    *,
    usage_id: str,
    candidate_list_id: str,
    eligible_targets: Sequence[str],
    candidate_targets: Sequence[str],
    readings: Sequence[DefinitionReading],
    inventory_gap: bool = False,
) -> StructuralProductReport:
    return StructuralProductReport(
        kind="definition_applicability",
        inputs=inputs,
        definition=DefinitionProduct(
            usage_id=usage_id,
            candidate_list_id=candidate_list_id,
            eligible_targets=tuple(eligible_targets),
            candidate_targets=tuple(candidate_targets),
            readings=tuple(readings),
            inventory_coverage="known_gap" if inventory_gap else "declared_selection",
        ),
    )


def compare_clauses(
    inputs: StructuralInput,
    *,
    left: ClauseReading,
    right: ClauseReading,
    cancelled: Callable[[], bool] = lambda: False,
) -> StructuralProductReport:
    if left.passage_id == right.passage_id:
        raise ValueError("comparison requires distinct original passages")
    passages = {p.passage_id: p for p in inputs.passages}
    if left.passage_id not in passages or right.passage_id not in passages:
        raise ValueError("clause outside selected passage closure")
    a, b = passages[left.passage_id], passages[right.passage_id]
    incompatible = a.scope != b.scope or a.effective_version != b.effective_version
    lf, rf = {f.dimension: f for f in left.fields}, {f.dimension: f for f in right.fields}
    dimensions = []
    for dimension in DIMENSIONS:
        if cancelled():
            raise InterruptedError("structural comparison cancelled")
        left_field, right_field = lf.get(dimension), rf.get(dimension)
        if left_field is None or right_field is None:
            outcome = "unknown"
        elif incompatible:
            outcome = "incompatible_applicability"
        else:
            outcome = (
                "same_lexical_value"
                if left_field.lexical_value == right_field.lexical_value
                else "different_lexical_value"
            )
        dimensions.append(
            DimensionComparison(
                dimension=dimension, outcome=outcome, left=left_field, right=right_field
            )
        )
    return StructuralProductReport(
        kind="qualified_comparison",
        inputs=inputs,
        comparison=ComparisonProduct(
            left_id=left.passage_id, right_id=right.passage_id, dimensions=tuple(dimensions)
        ),
    )


def assemble_dossier(
    inputs: StructuralInput,
    *,
    root_id: str,
    members: Sequence[DossierMember],
    representatives_per_group: int = 1,
    cancelled: Callable[[], bool] = lambda: False,
) -> StructuralProductReport:
    if type(representatives_per_group) is not int or representatives_per_group < 1:
        raise ValueError("representative group budget must be positive")
    order = {p.passage_id: (p.source_ref, p.start, p.end, p.passage_id) for p in inputs.passages}
    if any(m.passage_id not in order for m in members):
        raise ValueError("dossier member outside declared source closure")
    ordered = sorted(
        members,
        key=lambda m: (
            m.sense,
            m.role,
            m.scope,
            m.effective_version or "",
            order[m.passage_id],
            m.member_id,
        ),
    )
    counts: dict[tuple[str, str, str, str | None], int] = {}
    representatives = []
    for member in ordered:
        if cancelled():
            raise InterruptedError("dossier composition cancelled")
        key = (member.sense, member.role, member.scope, member.effective_version)
        count = counts.get(key, 0)
        if member.role in MANDATORY_ROLES or count < representatives_per_group:
            representatives.append(member.member_id)
        counts[key] = count + 1
    roles = {m.role for m in ordered}
    sections = (
        "definition",
        "terminology",
        "usage",
        "relationship",
        "variant",
        "exception",
        "revision",
        "conflict",
        "unresolved_sense",
        "open_question",
    )
    return StructuralProductReport(
        kind="dossier",
        inputs=inputs,
        dossier=DossierProduct(
            root_id=root_id,
            members=tuple(ordered),
            representatives=tuple(representatives),
            missing_sections=tuple(r for r in sections if r not in roles),
        ),
    )


# Registration is deliberately lightweight: retained report reads import no encoder.


class StructuralProductsConfig(StructuralValue):
    model_config = ConfigDict(frozen=True, extra="forbid")
    report: StructuralProductReport | None = None
    structural_input_digest: str | None = None

    @model_validator(mode="after")
    def bound_input(self) -> Self:
        expected = self.report.inputs.identity if self.report else None
        if self.structural_input_digest != expected:
            raise ValueError("structural configuration must name exact input manifest digest")
        return self


class StructuralProductsMethod:
    """Execute a frozen attributed reading through ordinary RUN task completion.

    Upstream retrieval/readings are supplied immutable inputs, not protected feedback.
    A default absent report selects no task and does not create a fabricated result.
    """

    name = "structure.products"
    version = "2"
    family = MethodFamily.CONSOLIDATE
    unit_type = TaskUnitType.RUN
    tier = MethodTier.DETERMINISTIC
    confidence_source = None
    Config = StructuralProductsConfig
    resources = Resources()

    def select(self, run, cfg):
        return (
            [UnitRef(TaskUnitType.RUN, unit_key=cfg.report.product_id)]
            if cfg.report is not None
            else []
        )

    def input_digest(self, unit, cfg):
        if cfg.report is None:
            raise ValueError("no structural report selected")
        from corpus_structure.semantic.identity import canonical_bytes

        return Digest(canonical_bytes(cfg.report.model_dump(mode="json")))

    def run(self, units, cfg, ctx):
        if cfg.report is None:
            raise ValueError("no structural report selected")
        return tuple(
            UnitResult(
                ref=unit.ref,
                outcome=ObservationOutcome.PRODUCED,
                structural_product=cfg.report.model_dump(mode="json"),
            )
            for unit in units
        )
