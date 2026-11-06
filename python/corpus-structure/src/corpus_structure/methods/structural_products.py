"""Compose attributed structural readings; similarity never supplies semantic support.

The operation accepts source-supported upstream readings. Native custody and public
admission remain separate boundaries; these producers emit only private proposals.
"""

from __future__ import annotations

from typing import Literal

from pydantic import Field, model_validator

from corpus_structure.core.method import Digest, Resources, UnitRef, UnitResult
from corpus_structure.core.vocab import MethodFamily, MethodTier, ObservationOutcome, TaskUnitType
from corpus_structure.semantic.retained_contributions import RetainedContributionRef
from corpus_structure.semantic.structural_products import (
    DIMENSIONS,
    MANDATORY_ROLES,
    ClauseReading,
    ComparisonProduct,
    DimensionComparison,
    DossierMember,
    DossierProduct,
    RetainedStructuralRef,
    StructuralInput,
    StructuralProductReport,
    StructuralValue,
)


def _difference(left, right):
    """Exact difference of same-direction threshold half-lines."""
    from decimal import Decimal

    from corpus_structure.semantic.structural_products import TriggerInterval

    a, b = Decimal(left.value), Decimal(right.value)
    if (
        left.comparator not in {">", ">=", "<", "<="}
        or right.comparator not in {">", ">=", "<", "<="}
        or left.comparator[0] != right.comparator[0]
    ):
        return None, None, "unsupported"
    if a == b:
        if left.comparator == right.comparator:
            return None, None, "equivalent"
        interval = TriggerInterval(lower=str(a), upper=str(a), lower_closed=True, upper_closed=True)
        return (
            (interval, None, "different")
            if "=" in left.comparator
            else (None, interval, "different")
        )
    low, high = (left, right) if a < b else (right, left)
    lower_side = left.comparator[0] == ">"
    interval = TriggerInterval(
        lower=low.value,
        upper=high.value,
        lower_closed=("=" in low.comparator) if lower_side else ("=" not in low.comparator),
        upper_closed=("=" not in high.comparator) if lower_side else ("=" in high.comparator),
    )
    removed = a < b if lower_side else a > b
    return (interval, None, "different") if removed else (None, interval, "different")


def compare_clauses(inputs, *, left, right, cancelled=lambda: False):
    if left.passage_id == right.passage_id:
        raise ValueError("comparison requires distinct original passages")
    passages = {p.passage_id: p for p in inputs.passages}
    if left.passage_id not in passages or right.passage_id not in passages:
        raise ValueError("clause outside selected passage closure")
    a, b = passages[left.passage_id], passages[right.passage_id]
    lf, rf = {f.dimension: f for f in left.fields}, {f.dimension: f for f in right.fields}
    dimensions = []
    for dimension in DIMENSIONS:
        if cancelled():
            raise InterruptedError("structural comparison cancelled")
        x, y = lf.get(dimension), rf.get(dimension)
        lexical = (
            "unknown"
            if x is None or y is None
            else "same_lexical_value"
            if x.lexical_value == y.lexical_value
            else "different_lexical_value"
        )
        typed, removed, added = "unknown", None, None
        reason = "No complete source-qualified typed premises."
        if x and y and x.typed and y.typed:
            p, q = x.typed, y.typed
            if "ambiguous" in {p.state, q.state}:
                typed = "ambiguous"
            elif "unsupported" in {p.state, q.state}:
                typed = "unsupported"
            elif (
                not p.unit
                or not q.unit
                or not p.quantity
                or p.quantity != q.quantity
                or p.unit != q.unit
                or p.basis != q.basis
            ):
                reason = "Unknown unit, quantity or basis withholds a stronger typed conclusion."
            else:
                removed, added, typed = _difference(p, q)
                reason = "Exact threshold consequence only; other rule dimensions remain separate."
        dimensions.append(
            DimensionComparison(
                dimension=dimension,
                outcome=lexical,
                left=x,
                right=y,
                typed_outcome=typed,
                removed_interval=removed,
                added_interval=added,
                assumptions=("same_quantity_unit_basis",)
                if typed in {"different", "equivalent"}
                else (),
                reason=reason,
            )
        )
    if a.scope != b.scope:
        applicability, reason = "differently_scoped", "Original source scopes differ."
    elif a.effective_version is None or b.effective_version is None:
        applicability, reason = "unestablished", "Effective versions are not established."
    elif a.effective_version != b.effective_version:
        applicability, reason = (
            "unestablished",
            "Different version labels do not establish succession or authority.",
        )
    elif all(
        d in lf and d in rf and lf[d].lexical_value == rf[d].lexical_value
        for d in DIMENSIONS
        if d != "threshold_unit"
    ):
        applicability, reason = (
            "co_applicable",
            "All non-threshold dimensions match under explicit scope/version.",
        )
    else:
        applicability, reason = (
            "unestablished",
            "Missing or changed applicability dimensions remain material.",
        )
    return StructuralProductReport(
        kind="qualified_comparison",
        inputs=inputs,
        comparison=ComparisonProduct(
            left_id=a.passage_id,
            right_id=b.passage_id,
            dimensions=tuple(dimensions),
            applicability=applicability,
            applicability_reason=reason,
        ),
    )


def read_clause(passage):
    from corpus_structure.semantic.structural_parsing import clause_fields, threshold_fields
    from corpus_structure.semantic.structural_products import (
        ClauseField,
        LocatedDefinitionSpan,
        TypedPremise,
    )

    readings = []
    for dimension, field in clause_fields(passage.text).items():
        readings.append(
            ClauseField(
                dimension=dimension,
                lexical_value=field["text"],
                evidence=(passage.passage_id,),
                span=LocatedDefinitionSpan(
                    passage_id=passage.passage_id,
                    start=passage.start + field["start"],
                    end=passage.start + field["end"],
                    text=field["text"],
                ),
            )
        )
    # These are the authenticated input context, not textually observed version/parent claims.
    for dimension, value in (("parent", passage.parent), ("version", passage.effective_version)):
        if value:
            readings.append(
                ClauseField(
                    dimension=dimension, lexical_value=value, evidence=(passage.passage_id,)
                )
            )
    fields = threshold_fields(passage.text)
    if len(fields) == 1:
        f = fields[0]
        readings.append(
            ClauseField(
                dimension="threshold_unit",
                lexical_value=f["text"],
                evidence=(passage.passage_id,),
                typed=TypedPremise(
                    span=LocatedDefinitionSpan(
                        passage_id=passage.passage_id,
                        start=passage.start + f["start"],
                        end=passage.start + f["end"],
                        text=f["text"],
                    ),
                    grammar=f["grammar"],
                    state="parsed",
                    value=f["value"],
                    comparator=f["comparator"],
                    quantity=f["quantity"],
                    unit=f["unit"],
                ),
            )
        )
    return ClauseReading(passage_id=passage.passage_id, fields=tuple(readings))


def select_dossier(
    inputs,
    *,
    root_id,
    members,
    supported_facets=(),
    predecessors=(),
    contribution_predecessors=(),
    member_budget=12,
    policy="supported-facet-greedy-1",
    cancelled=lambda: False,
):
    """Represent an already authenticated membership; this never grants support."""
    from hashlib import sha256

    from corpus_structure.semantic.identity import canonical_bytes
    from corpus_structure.semantic.structural_products import DossierRepresentation

    if type(member_budget) is not int or member_budget < 1:
        raise ValueError("dossier budget must be positive")
    if policy not in {"supported-facet-greedy-1", "source-order-control-1"}:
        raise ValueError("unsupported representation policy")
    passages = {p.passage_id: p for p in inputs.passages}

    def order(m):
        return (passages[m.passage_id].source_ref, m.citation.start, m.citation.end, m.member_id)

    ordered = tuple(sorted(members, key=order))
    ids = {m.member_id for m in ordered}
    if any(f.member_id not in ids for f in supported_facets):
        raise ValueError("facet lies outside dossier membership")
    facets = tuple(sorted(supported_facets, key=lambda f: f.facet_id))
    # Repeated evidence for one facet is not multiple coverage. Facet identity includes
    # its semantic kind/scope, while member identity supplies the supporting witness.
    coverage = {
        m.member_id: {(f.kind, f.scope) for f in facets if f.member_id == m.member_id}
        for m in ordered
    }
    selected = [m for m in ordered if m.role in MANDATORY_ROLES]
    seen = set().union(*(coverage[m.member_id] for m in selected)) if selected else set()
    remaining = [m for m in ordered if m.member_id not in {x.member_id for x in selected}]
    while remaining and len(selected) < member_budget:
        if cancelled():
            raise InterruptedError("dossier composition cancelled")
        if policy == "source-order-control-1":
            chosen = remaining[0]
        else:
            chosen = min(remaining, key=lambda m: (-len(coverage[m.member_id] - seen), order(m)))
        selected.append(chosen)
        remaining.remove(chosen)
        seen.update(coverage[chosen.member_id])
    chosen = tuple(m.member_id for m in selected)
    represented = tuple(f.facet_id for f in facets if f.member_id in chosen)
    representation = DossierRepresentation(
        policy=policy,
        member_budget=member_budget,
        selected=chosen,
        omitted=tuple(m.member_id for m in ordered if m.member_id not in chosen),
        represented_facets=represented,
        missing_facets=tuple(f.facet_id for f in facets if f.facet_id not in represented),
        mandatory_overflow=sum(m.role in MANDATORY_ROLES for m in ordered) > member_budget,
        membership_digest=sha256(
            canonical_bytes([m.model_dump(mode="json", exclude_none=True) for m in ordered])
        ).hexdigest(),
        facet_digest=sha256(
            canonical_bytes([f.model_dump(mode="json", exclude_none=True) for f in facets])
        ).hexdigest(),
    )
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
            members=ordered,
            predecessors=tuple(predecessors),
            contribution_predecessors=tuple(contribution_predecessors),
            representatives=chosen,
            missing_sections=tuple(r for r in sections if r not in roles),
            supported_facets=facets,
            representation=representation,
        ),
    )


def derive_dossier_members(inputs, retained):
    """Derive role spans from actual retained products, never from input inventory."""
    from hashlib import sha256

    from corpus_structure.semantic.identity import canonical_bytes
    from corpus_structure.semantic.structural_admission import structural_statement
    from corpus_structure.semantic.structural_products import (
        DefinitionInterpretation,
        DefinitionOutcome,
        DossierFacet,
        LocatedDefinitionSpan,
        MemberRole,
    )

    passages = {p.passage_id: p for p in inputs.passages}
    members = []
    facets = []
    for reference, payload in retained:
        report = StructuralProductReport.model_validate(payload["report"])
        if report.product_id != reference.product_id:
            raise ValueError("retained predecessor product substituted")
        if report.product_id not in inputs.dependencies:
            raise ValueError("dossier predecessor outside declared dependencies")
        for p in report.inputs.passages:
            if p.passage_id not in passages or passages[p.passage_id] != p:
                raise ValueError("predecessor original source passage differs from dossier closure")
        roles: list[
            tuple[
                MemberRole,
                LocatedDefinitionSpan,
                str | None,
                DefinitionInterpretation | None,
                DefinitionOutcome | None,
            ]
        ] = []

        def content_role(
            interpretation: DefinitionInterpretation, outcome: DefinitionOutcome | None = None
        ) -> MemberRole:
            if outcome == "incompatible":
                return "relationship"
            if outcome in {"mention", "example", "applicable_explanation"}:
                return "usage"
            if outcome == "unresolved" or interpretation == "unresolved":
                return "unresolved_sense"
            return "usage" if interpretation == "explanation" else "definition"

        if report.definition_components:
            for c in report.definition_components.components:
                roles.extend(
                    (
                        ("terminology", c.term, c.component_id, c.interpretation, None),
                        (
                            content_role(c.interpretation),
                            c.content,
                            c.component_id,
                            c.interpretation,
                            None,
                        ),
                    )
                )
        if report.definition:
            p = passages[report.definition.usage_id]
            roles.append(
                (
                    "usage",
                    LocatedDefinitionSpan(
                        passage_id=p.passage_id, start=p.start, end=p.end, text=p.text
                    ),
                    None,
                    None,
                    None,
                )
            )
            for r in report.definition.readings:
                roles.append(
                    (
                        content_role(r.component.interpretation, r.outcome),
                        r.component.content,
                        None,
                        r.component.interpretation,
                        r.outcome,
                    )
                )
        if report.comparison:
            for d in report.comparison.dimensions:
                for side in (d.left, d.right):
                    if side:
                        span = side.span or (side.typed.span if side.typed else None)
                        if span is not None:
                            roles.append(
                                (
                                    "exception" if d.dimension == "exception" else "variant",
                                    span,
                                    None,
                                    None,
                                    None,
                                )
                            )
        for role, span, component_id, interpretation, outcome in roles:
            p = passages[span.passage_id]
            key = sha256(
                canonical_bytes(
                    dict(
                        product=report.product_id,
                        role=role,
                        citation=span.model_dump(mode="json"),
                        **(
                            {"definition_interpretation": interpretation}
                            if interpretation is not None
                            else {}
                        ),
                        **({"applicability_outcome": outcome} if outcome is not None else {}),
                    )
                )
            ).hexdigest()
            supported = None
            expected = (
                None
                if report.definition_components and interpretation == "unresolved"
                else structural_statement(report, component_id)
                if report.definition_components
                else structural_statement(report)
            )
            # Native supplies only protected existing assertions, not producer confidence.
            # Exact statement equality prevents borrowing an assessment of another role,
            # physical source, interpretation, or incomplete predecessor.
            for assertion in payload.get("public_assertions", ()):
                if (
                    expected is not None
                    and assertion.get("statement") == expected
                    and assertion.get("assessment_id")
                ):
                    supported = assertion["assessment_id"]
                    break
            member = DossierMember(
                member_id=key,
                passage_id=p.passage_id,
                citation=span,
                role=role,
                sense="unresolved",
                scope=p.scope,
                effective_version=p.effective_version,
                relation_product_id=report.product_id,
                definition_interpretation=interpretation,
                applicability_outcome=outcome,
                qualification="independently_supported" if supported else "proposed",
                assessment_id=supported,
            )
            if member.member_id in {m.member_id for m in members}:
                continue
            members.append(member)
            if supported:
                semantic_kind = ":".join(
                    value for value in (role, interpretation, outcome) if value is not None
                )
                facet_kind = semantic_kind + ":" + span.text
                facets.append(
                    DossierFacet(
                        facet_id=key + ":" + role,
                        kind=facet_kind,
                        definition_interpretation=interpretation,
                        applicability_outcome=outcome,
                        scope=p.scope,
                        member_id=key,
                        assessment_id=supported,
                        evidence=(p.passage_id,),
                    )
                )
    return tuple(members), tuple(facets)


class StructuralComparisonConfig(StructuralValue):
    inputs: StructuralInput | None = None
    structural_input_digest: str | None = None
    left_id: str | None = None
    right_id: str | None = None

    @model_validator(mode="after")
    def bound_input(self):
        if self.inputs is None:
            if any((self.structural_input_digest, self.left_id, self.right_id)):
                raise ValueError("partial comparison config")
        elif (
            self.structural_input_digest != self.inputs.identity
            or self.left_id == self.right_id
            or not {self.left_id, self.right_id} <= {p.passage_id for p in self.inputs.passages}
        ):
            raise ValueError("comparison requires exact inputs and two selected passages")
        return self


class StructuralComparisonMethod:
    name = "structure.compare"
    version = "1"
    family = MethodFamily.CONSOLIDATE
    unit_type = TaskUnitType.RUN
    tier = MethodTier.DETERMINISTIC
    confidence_source = None
    Config = StructuralComparisonConfig
    resources = Resources()

    def select(self, run, cfg) -> tuple[UnitRef, ...]:
        return (UnitRef(TaskUnitType.RUN, unit_key=cfg.inputs.identity),) if cfg.inputs else ()

    def input_digest(self, unit, cfg):
        from corpus_structure.semantic.identity import canonical_bytes

        return Digest(canonical_bytes(cfg.model_dump(mode="json")))

    def run(self, units, cfg, ctx):
        if cfg.inputs is None:
            raise ValueError("comparison inputs absent")
        ctx.check_active()
        passages = {p.passage_id: p for p in cfg.inputs.passages}
        report = compare_clauses(
            cfg.inputs,
            left=read_clause(passages[cfg.left_id]),
            right=read_clause(passages[cfg.right_id]),
        )
        return tuple(
            UnitResult(
                ref=u.ref,
                outcome=ObservationOutcome.PRODUCED,
                structural_product=report.model_dump(mode="json"),
            )
            for u in units
        )


class StructuralDossierConfig(StructuralValue):
    inputs: StructuralInput | None = None
    structural_input_digest: str | None = None
    root_id: str | None = None
    predecessors: tuple[RetainedStructuralRef, ...] = ()
    contribution_predecessors: tuple[RetainedContributionRef, ...] = ()
    member_budget: int = Field(default=12, gt=0, strict=True)
    policy: Literal["supported-facet-greedy-1", "source-order-control-1"] = (
        "supported-facet-greedy-1"
    )

    @model_validator(mode="after")
    def bound_input(self):
        if self.inputs is None:
            if (
                self.structural_input_digest
                or self.root_id
                or self.predecessors
                or self.contribution_predecessors
            ):
                raise ValueError("partial dossier config")
        elif (
            self.structural_input_digest != self.inputs.identity
            or not self.root_id
            or not (self.predecessors or self.contribution_predecessors)
        ):
            raise ValueError("dossier requires original inputs and retained predecessors")
        if len({p.product_id for p in self.predecessors}) != len(self.predecessors):
            raise ValueError("duplicate dossier predecessor")
        if len({p.contribution_id for p in self.contribution_predecessors}) != len(
            self.contribution_predecessors
        ):
            raise ValueError("duplicate dossier contribution predecessor")
        return self


class StructuralDossierMethod:
    name = "structure.dossier"
    version = "1"
    family = MethodFamily.CONSOLIDATE
    unit_type = TaskUnitType.RUN
    tier = MethodTier.DETERMINISTIC
    confidence_source = None
    Config = StructuralDossierConfig
    resources = Resources()

    def select(self, run, cfg) -> tuple[UnitRef, ...]:
        return (UnitRef(TaskUnitType.RUN, unit_key=cfg.inputs.identity),) if cfg.inputs else ()

    def input_digest(self, unit, cfg):
        from corpus_structure.semantic.identity import canonical_bytes

        return Digest(canonical_bytes(cfg.model_dump(mode="json")))

    def run(self, units, cfg, ctx):
        if cfg.inputs is None:
            raise ValueError("dossier inputs absent")
        retained = []
        for reference in cfg.predecessors:
            ctx.check_active()
            retained.append((reference, ctx.reader.retained_structural_report(reference)))
        members, facets = derive_dossier_members(cfg.inputs, retained)
        from .dossier_contributions import derive_contribution_members

        source_members = []
        for reference in cfg.contribution_predecessors:
            ctx.check_active()
            payload = ctx.reader.retained_source_contribution(reference)
            source_members.extend(derive_contribution_members(cfg.inputs, reference, payload))
        members = (*members, *source_members)
        report = select_dossier(
            cfg.inputs,
            root_id=cfg.root_id,
            members=members,
            supported_facets=facets,
            predecessors=cfg.predecessors,
            contribution_predecessors=cfg.contribution_predecessors,
            member_budget=cfg.member_budget,
            policy=cfg.policy,
        )
        return tuple(
            UnitResult(
                ref=u.ref,
                outcome=ObservationOutcome.PRODUCED,
                structural_product=report.model_dump(mode="json"),
            )
            for u in units
        )
