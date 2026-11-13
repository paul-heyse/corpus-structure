"""Compose attributed structural readings; similarity never supplies semantic support.

The operation accepts source-supported upstream readings. Native custody and public
admission remain separate boundaries; these producers emit only private proposals.
"""

from __future__ import annotations

from collections import defaultdict
from hashlib import sha256
from itertools import pairwise
from typing import Any, ClassVar, Literal

from pydantic import Field, model_validator

from corpus_structure.core.method import Digest, Resources, UnitRef, UnitResult
from corpus_structure.core.vocab import MethodFamily, MethodTier, ObservationOutcome, TaskUnitType
from corpus_structure.semantic.data_operation_bindings import BindingResult
from corpus_structure.semantic.data_operation_consumers import BoundConsumerSelection
from corpus_structure.semantic.formal_readings import (
    FormalSourceReadings,
    comparison_basis_readings,
    coordination_reading,
    formal_field_readings,
    lexical_fact_readings,
)
from corpus_structure.semantic.identity import canonical_bytes
from corpus_structure.semantic.retained_contributions import RetainedContributionRef
from corpus_structure.semantic.structural_products import (
    DIMENSIONS,
    MANDATORY_ROLES,
    ClauseField,
    ClauseFieldGroup,
    ClauseReading,
    ComparisonLiteral,
    ComparisonMemberDecision,
    ComparisonProduct,
    DimensionComparison,
    DossierComparisonBinding,
    DossierComparisonSelection,
    DossierMember,
    DossierProduct,
    LocatedDefinitionComponent,
    LocatedDefinitionSpan,
    RetainedComponentRef,
    RetainedStructuralRef,
    RevisionSuccession,
    StructuralInput,
    StructuralProductReport,
    StructuralValue,
)


def _located(passage, text: str, start: int) -> LocatedDefinitionSpan:
    return LocatedDefinitionSpan(
        passage_id=passage.passage_id,
        start=passage.start + start,
        end=passage.start + start + len(text),
        text=text,
    )


def _succession(left, right, *, sources, primary_layers) -> RevisionSuccession | None:
    if primary_layers is None or not left.effective_version or not right.effective_version:
        return None
    if (
        left.effective_version == right.effective_version
        or not left.parent
        or left.parent != right.parent
        or left.source_ref != right.source_ref
        or not (left.end <= right.start or right.end <= left.start)
    ):
        return None
    lineages = {}
    for passage in (left, right):
        facts = lexical_fact_readings(
            primary_layers,
            sources[passage.source_ref],
            kind="formal.clause_lineage",
            start=passage.start,
            end=passage.end,
        )
        if len(facts) != 1 or facts[0].value != left.parent:
            return None
        lineages[passage.passage_id] = facts[0]
    witnesses = []
    for newer, older in ((left, right), (right, left)):
        declarations = lexical_fact_readings(
            primary_layers,
            sources[older.source_ref],
            kind="formal.revision_declaration",
            start=older.start,
            end=older.end,
        )
        if len(declarations) != 1 or declarations[0].value != older.effective_version:
            continue
        (declaration,) = declarations
        successions = lexical_fact_readings(
            primary_layers,
            sources[newer.source_ref],
            kind="formal.revision_succession",
            start=newer.start,
            end=newer.end,
        )
        for fact in successions:
            values = {role: value for role, _reference, value in fact.bindings}
            if len(fact.bindings) != 2 or values != dict(
                newer_revision=newer.effective_version, older_revision=older.effective_version
            ):
                continue
            witnesses.append(
                RevisionSuccession(
                    older_id=older.passage_id,
                    newer_id=newer.passage_id,
                    evidence=_located(newer, fact.text, fact.start - newer.start),
                    older_evidence=_located(
                        older, declaration.text, declaration.start - older.start
                    ),
                    primary_witnesses=(
                        declaration.reference,
                        fact.reference,
                        lineages[older.passage_id].reference,
                        lineages[newer.passage_id].reference,
                    ),
                )
            )
    return witnesses[0] if len(witnesses) == 1 else None


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


def _typed_member(field):
    """Return the comparable question and exact value for a source-backed member."""
    threshold = field.typed
    if (
        threshold is not None
        and threshold.state == "parsed"
        and threshold.quantity
        and threshold.unit
        and threshold.basis
    ):
        return (
            ("threshold", threshold.quantity, threshold.unit, threshold.basis),
            (threshold.comparator, threshold.value),
        )
    if field.literal is not None and field.literal.kind in {"date", "identifier"}:
        return ((field.literal.kind,), field.literal.value)
    condition = field.condition
    if condition is not None:
        negated = condition.get("kind") == "not"
        comparison = condition.get("term", {}) if negated else condition
        if comparison.get("kind") == "compare":
            return (
                ("condition", negated),
                (comparison["lhs"], comparison["relation"], comparison["rhs"]),
            )
    return None


def _compare_group_members(
    left, right, *, compatible
) -> tuple[
    Literal["same", "different", "unresolved"],
    tuple[ComparisonMemberDecision, ...],
    Literal["unknown", "ambiguous", "different", "equivalent"],
]:
    if not compatible:
        return "unresolved", (), "unknown"
    if "unresolved" in (left.state, right.state, left.grouping, right.grouping):
        return "unresolved", (), "ambiguous"
    if "absent" in (left.state, right.state):
        return "unresolved", (), "unknown"
    grouping: Literal["same", "different"] = (
        "same" if left.grouping == right.grouping else "different"
    )
    by_side = []
    for group in (left, right):
        by_key = defaultdict(list)
        for index, field in enumerate(group.members):
            typed = _typed_member(field)
            if typed is not None:
                key, value = typed
                by_key[key].append((index, value))
        by_side.append(by_key)
    lkeys, rkeys = by_side
    matched = []
    ambiguous = False
    for key in lkeys.keys() & rkeys.keys():
        if len(lkeys[key]) != 1 or len(rkeys[key]) != 1:
            ambiguous = True
            continue
        (li, lv), (ri, rv) = lkeys[key][0], rkeys[key][0]
        matched.append(
            ComparisonMemberDecision(
                left_index=li, right_index=ri, outcome="equivalent" if lv == rv else "different"
            )
        )
    matched.sort(key=lambda row: row.left_index)
    outcome: Literal["unknown", "ambiguous", "different", "equivalent"]
    if ambiguous:
        outcome = "ambiguous"
    elif len(matched) != len(left.members) or len(matched) != len(right.members) or not matched:
        outcome = "unknown"
    elif grouping == "different" or any(row.outcome == "different" for row in matched):
        outcome = "different"
    else:
        outcome = "equivalent"
    return grouping, tuple(matched), outcome


def compare_clauses(
    inputs,
    *,
    left,
    right,
    left_reading=None,
    right_reading=None,
    cancelled=lambda: False,
    typed_groups=False,
    primary_layers=None,
):
    if left.passage_id == right.passage_id:
        raise ValueError("comparison requires distinct original passages")
    passages = {p.passage_id: p for p in inputs.passages}
    if left.passage_id not in passages or right.passage_id not in passages:
        raise ValueError("clause outside selected passage closure")
    a, b = passages[left.passage_id], passages[right.passage_id]
    grouped = left.groups is not None and right.groups is not None
    if grouped != (left_reading is not None and right_reading is not None):
        raise ValueError("grouped comparison requires retained reading references")
    lf, rf = {f.dimension: f for f in left.fields}, {f.dimension: f for f in right.fields}
    succession = (
        _succession(
            a,
            b,
            sources={source.identity: source for source in inputs.sources},
            primary_layers=primary_layers,
        )
        if a.scope == b.scope
        else None
    )
    compatible = a.scope == b.scope and (
        a.effective_version == b.effective_version or succession is not None
    )
    typed_compatible = compatible and (a.effective_version is not None or succession is not None)
    interval_applicable = not typed_groups or (
        typed_compatible
        and all(
            "unresolved" not in (group.state, group.grouping)
            for side in (left, right)
            for group in (side.groups or {}).values()
        )
    )
    dimensions = []
    for dimension in DIMENSIONS:
        if cancelled():
            raise InterruptedError("structural comparison cancelled")
        lg, rg = (left.groups[dimension], right.groups[dimension]) if grouped else (None, None)
        if lg is not None and rg is not None:
            x, y = (
                group.members[0]
                if group.state == "present" and group.grouping == "singleton"
                else None
                for group in (lg, rg)
            )
        else:
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
        grouping = matched = None
        if lg is not None and rg is not None:
            values = tuple(
                tuple(member.lexical_value for member in group.members) for group in (lg, rg)
            )
            if lg.state in {"present", "empty"} and rg.state in {"present", "empty"}:
                lexical = (
                    "same_lexical_value" if values[0] == values[1] else "different_lexical_value"
                )
            if not compatible:
                lexical = "incompatible_applicability"
            elif "unresolved" in (lg.state, rg.state, lg.grouping, rg.grouping):
                typed = "ambiguous"
            if typed_groups:
                grouping, matched, typed = _compare_group_members(
                    lg, rg, compatible=typed_compatible
                )
                if matched:
                    reason = "Compared source-qualified members by their unique typed keys."
        threshold_consequence = False
        if interval_applicable and (not grouped or compatible) and x and y and x.typed and y.typed:
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
                or not p.basis
                or not q.basis
                or p.basis != q.basis
            ):
                reason = "Unknown unit, quantity or basis withholds a stronger typed conclusion."
            else:
                removed, added, typed = _difference(p, q)
                threshold_consequence = True
                reason = "Exact threshold consequence only; other rule dimensions remain separate."
        dimensions.append(
            DimensionComparison(
                dimension=dimension,
                outcome=lexical,
                **({"left_group": lg, "right_group": rg} if grouped else {"left": x, "right": y}),
                grouping_outcome=grouping,
                member_comparisons=matched,
                typed_outcome=typed,
                removed_interval=removed,
                added_interval=added,
                assumptions=("same_quantity_unit_basis",)
                if threshold_consequence and typed in {"different", "equivalent"}
                else (),
                reason=reason,
            )
        )
    if a.scope != b.scope:
        applicability, reason = "differently_scoped", "Original source scopes differ."
    elif succession is not None:
        applicability, reason = "successive_revisions", "Exact source text establishes succession."
    elif a.effective_version is None or b.effective_version is None:
        applicability, reason = "unestablished", "Effective versions are not established."
    elif a.effective_version != b.effective_version:
        applicability, reason = (
            "unestablished",
            "Different version labels do not establish succession or authority.",
        )
    elif (
        all(
            comparison.outcome == "same_lexical_value"
            and comparison.left_group is not None
            and comparison.right_group is not None
            and comparison.left_group.grouping == comparison.right_group.grouping
            and comparison.left_group.grouping != "unresolved"
            for comparison in dimensions
            if comparison.dimension != "threshold_unit"
        )
        if grouped
        else all(
            d in lf and d in rf and lf[d].lexical_value == rf[d].lexical_value
            for d in DIMENSIONS
            if d != "threshold_unit"
        )
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
            left_reading=left_reading,
            right_reading=right_reading,
            left_focus=left.focus if typed_groups else None,
            right_focus=right.focus if typed_groups else None,
            dimensions=tuple(dimensions),
            applicability=applicability,
            applicability_reason=reason,
            succession=succession,
        ),
    )


def _threshold_inventory(passage, source, primary_layers):
    from corpus_structure.semantic.structural_products import TypedPremise

    if source is None or primary_layers is None:
        return (), False
    fields, complete = formal_field_readings(
        primary_layers, source, family="formal.threshold", start=passage.start, end=passage.end
    )
    bases = comparison_basis_readings(primary_layers, source, start=passage.start, end=passage.end)
    basis = bases[0] if len(bases) == 1 else None
    results = []
    for field in fields:
        if passage.text[field.start - passage.start : field.end - passage.start] != field.text:
            raise ValueError("retained threshold differs from the exact selected passage")
        value = field.normalized
        if value.get("kind") != "threshold" or "value" not in value or "comparator" not in value:
            complete = False
            continue
        results.append(
            ClauseField(
                dimension="threshold_unit",
                lexical_value=field.text,
                evidence=(passage.passage_id,),
                typed=TypedPremise(
                    span=_located(passage, field.text, field.start - passage.start),
                    grammar=field.grammar,
                    state="parsed",
                    value=value["value"],
                    comparator=value["comparator"],
                    quantity=value.get("quantity"),
                    unit=value.get("unit"),
                    primary_formal=field.reference,
                    basis=None if basis is None else basis.value,
                    basis_evidence=None
                    if basis is None
                    else _located(passage, basis.text, basis.start - passage.start),
                    primary_basis=None if basis is None else basis.reference,
                ),
            )
        )
    return tuple(results), complete


def threshold_readings(passage, *, source=None, primary_layers=None):
    """Project retained whole threshold rules; missing primary evidence is unresolved."""
    return _threshold_inventory(passage, source, primary_layers)[0]


def _literal_reading(span, source, primary_layers):
    if primary_layers is None or len(span.text) > 256:
        return None, None
    offered = []
    for family in ("formal.date", "formal.identifier", "formal.quantity", "formal.interval"):
        fields, _complete = formal_field_readings(
            primary_layers, source, family=family, start=span.start, end=span.end
        )
        offered.extend(
            field
            for field in fields
            if field.start == span.start
            and field.end == span.end
            and field.text == span.text
            and field.start_symbol == "labeled"
        )
    if len(offered) != 1:
        return None, None
    (field,) = offered
    value = field.normalized
    if value["kind"] in {"date", "identifier"}:
        literal = dict(kind=value["kind"], value=value["value"])
    elif field.rule == "quantity" and "unit" in value:
        literal = dict(kind="quantity", value=value["value"], unit=value["unit"])
    elif value["kind"] == "interval" and "unit" in value:
        literal = dict(
            kind="range",
            **{
                key: value[key]
                for key in ("lower", "upper", "lower_closed", "upper_closed", "unit")
            },
        )
    else:
        return None, None
    try:
        return ComparisonLiteral.model_validate(literal), field.reference
    except ValueError:
        # Exact primary syntax remains available outside this bounded domain projection.
        return None, None


_ROLE_DIMENSIONS = {"actor": "actor", "predicate": "action", "object": "object"}
_QUALIFIER_DIMENSIONS = {
    "condition": "condition",
    "assumption": "condition",
    "exception": "exception",
    "modality": "modality",
    "order": "order_dependency",
    "dependency": "order_dependency",
}


def comparison_host_evidence(component, frame, frame_id):
    return (
        component.get("kind") == "predicate_qualifier"
        and component.get("host_contribution_id") == frame_id
    ) or (
        component.get("kind") == "predicate_cue"
        and component.get("host_state") == "unresolved"
        and component.get("scope") == frame.get("scope")
        and component.get("annotation") == frame.get("annotation")
        and frame.get("predicate_token") in component.get("candidate_tokens", ())
    )


def _group_fields(passage, members, incomplete, *, source=None, primary_layers=None):
    def extents(member):
        if member.spans is not None:
            return member.spans
        if member.typed is not None:
            return (member.typed.span,)
        return ()

    def order(member):
        spans = extents(member)
        return (spans[0].start if spans else passage.end, member.contribution_id or "")

    ordered = tuple(sorted(members, key=order))
    if not ordered:
        return ClauseFieldGroup(state="unresolved" if incomplete else "absent")
    if incomplete:
        return ClauseFieldGroup(state="unresolved", grouping="unresolved", members=ordered)
    if len(ordered) == 1:
        return ClauseFieldGroup(state="present", grouping="singleton", members=ordered)
    connectors, facts = [], []
    for left, right in pairwise(ordered):
        left_spans, right_spans = extents(left), extents(right)
        if not left_spans or not right_spans or source is None or primary_layers is None:
            return ClauseFieldGroup(state="present", grouping="unresolved", members=ordered)
        fact = coordination_reading(
            primary_layers, source, start=left_spans[-1].end, end=right_spans[0].start
        )
        if fact is None:
            return ClauseFieldGroup(state="present", grouping="unresolved", members=ordered)
        facts.append(fact)
        connectors.append(_located(passage, fact.text, fact.start - passage.start))
    words = {fact.value for fact in facts}
    if len(words) != 1 or not words <= {"and", "or"}:
        return ClauseFieldGroup(state="present", grouping="unresolved", members=ordered)
    return ClauseFieldGroup(
        state="present",
        grouping="conjunction" if words == {"and"} else "disjunction",
        members=ordered,
        witnesses=tuple(connectors),
        primary_witnesses=tuple(fact.reference for fact in facts),
    )


def read_retained_clause(
    passage, source, reference, retained, *, predicate_version=None, primary_layers=None
):
    """Compose the admitted frame roles and the immutable host qualifier population."""
    if reference.project_id != source.project_id:
        raise ValueError("reading belongs to another project")
    primary = FormalSourceReadings(primary_layers, source) if primary_layers is not None else None
    rows = {row["contribution_id"]: row for row in retained["contributions"]}
    reading = rows[reference.contribution_id]
    component = reading.get("component", {})
    if component.get("kind") != "predicate_reading" or (
        predicate_version is not None and component.get("question_version") != predicate_version
    ):
        raise ValueError("comparison requires a retained predicate reading")
    frame = rows[component["frame"]]
    frame_component = frame.get("component", {})
    pin = reading["pin"]
    if (
        frame_component.get("kind") != "predicate_frame"
        or frame["pin"] != pin
        or pin.get("source_view_id") != source.source_view_id
        or pin.get("product_digest") != source.native_content_digest
        or pin.get("native_product_task_id") != source.native_task_id
        or pin.get("projection_digest") != source.projection_digest
        or pin.get("recipe_digest") != source.recipe_digest
        or any(
            part.get("scope") != passage.passage_id
            or part.get("effective_version") != passage.effective_version
            for part in (component, frame_component)
        )
    ):
        raise ValueError("retained frame differs from exact selected passage")

    members = {dimension: [] for dimension in DIMENSIONS}
    incomplete = set()

    def located(dimension, extents, contribution_id, condition=None):
        spans = []
        for extent in extents:
            start, end = extent["start"], extent["end"]
            if not passage.start <= start < end <= passage.end:
                raise ValueError("comparison extent outside selected passage")
            spans.append(
                _located(
                    passage,
                    passage.text[start - passage.start : end - passage.start],
                    start - passage.start,
                )
            )
        if not spans:
            incomplete.add(dimension)
            return
        literal, primary_formal = (
            _literal_reading(spans[0], source, primary) if len(spans) == 1 else (None, None)
        )
        members[dimension].append(
            ClauseField(
                dimension=dimension,
                lexical_value=" ".join(span.text for span in spans),
                spans=tuple(spans),
                evidence=(passage.passage_id,),
                contribution_id=contribution_id,
                condition=condition,
                literal=literal,
                primary_formal=primary_formal,
            )
        )

    focus = None
    for role in frame_component.get("unlocated_roles", ()):
        if dimension := _ROLE_DIMENSIONS.get(role["role"]):
            incomplete.add(dimension)
    for role in frame_component["frame_members"]:
        if role["role"] == "focus" and role["outcome"] == "complete" and len(role["extents"]) == 1:
            focus = role["extents"][0]
        dimension = _ROLE_DIMENSIONS.get(role["role"])
        if dimension is not None:
            located(dimension, role["extents"], role["contribution"])
            if role["outcome"] != "complete":
                incomplete.add(dimension)
    for row in rows.values():
        qualifier = row.get("component", {})
        if (
            qualifier.get("kind") == "predicate_cue"
            and comparison_host_evidence(qualifier, frame_component, frame["contribution_id"])
            and (dimension := _QUALIFIER_DIMENSIONS.get(qualifier["cue_kind"]))
        ):
            incomplete.add(dimension)
        if (
            qualifier.get("kind") == "predicate_qualifier"
            and qualifier.get("host_contribution_id") == frame["contribution_id"]
            and (dimension := _QUALIFIER_DIMENSIONS.get(qualifier["qualifier_kind"]))
        ):
            cue = rows[qualifier["qualifier_contribution_id"]]
            if cue["pin"] != pin:
                raise ValueError("comparison qualifier differs from selected source")
            located(
                dimension,
                cue["component"]["extents"],
                row["contribution_id"],
                qualifier.get("condition"),
            )
    for dimension, value in (("parent", passage.parent), ("version", passage.effective_version)):
        if value is not None:
            members[dimension].append(
                ClauseField(
                    dimension=dimension, lexical_value=value, evidence=(passage.passage_id,)
                )
            )
    # A threshold has authority only in the admitted focus or a located condition.
    controls = [
        (span.start, span.end) for member in members["condition"] for span in member.spans or ()
    ]
    if focus is not None:
        controls.append((focus["start"], focus["end"]))
    thresholds, complete_thresholds = _threshold_inventory(passage, source, primary)
    if not complete_thresholds:
        incomplete.add("threshold_unit")
    for field in thresholds:
        if (
            field.dimension == "threshold_unit"
            and field.typed is not None
            and any(
                lo <= field.typed.span.start < field.typed.span.end <= hi for lo, hi in controls
            )
        ):
            members[field.dimension].append(field)
    groups = {
        dimension: _group_fields(
            passage, fields, dimension in incomplete, source=source, primary_layers=primary
        )
        for dimension, fields in members.items()
    }
    exception_spans = [span for field in groups["exception"].members for span in field.spans or ()]
    located_focus = None
    if focus is not None:
        start, end = focus["start"] - passage.start, focus["end"] - passage.start
        located_focus = _located(passage, passage.text[start:end], start)
        exception_spans.append(located_focus)
    empty = []
    if primary is not None:
        for span in exception_spans:
            facts = lexical_fact_readings(
                primary, source, kind="formal.exception_empty", start=span.start, end=span.end
            )
            if len(facts) == 1:
                (fact,) = facts
                # Only source whitespace and the optional original terminator may
                # surround the explicitly classified marker; no lexical inference.
                left = span.text[: fact.start - span.start]
                right = span.text[fact.end - span.start :]
                if not left.strip() and right.strip() in {"", "."}:
                    empty.append(fact)
    if len(empty) == 1 and (
        not groups["exception"].members
        or (
            len(groups["exception"].members) == 1
            and len(groups["exception"].members[0].spans or ()) == 1
        )
    ):
        (fact,) = empty
        groups["exception"] = ClauseFieldGroup(
            state="empty",
            witnesses=(_located(passage, fact.text, fact.start - passage.start),),
            primary_witnesses=(fact.reference,),
        )
    condition = groups["condition"]
    threshold = groups["threshold_unit"]
    if threshold.members and "unresolved" in (condition.state, condition.grouping):
        groups["threshold_unit"] = ClauseFieldGroup(
            state="unresolved", grouping="unresolved", members=threshold.members
        )
    return ClauseReading(
        passage_id=passage.passage_id,
        groups=groups,
        focus=located_focus,
    )


def select_dossier(
    inputs,
    *,
    root_id,
    root_component=None,
    members,
    supported_facets=(),
    predecessors=(),
    contribution_predecessors=(),
    comparison_selections=(),
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
            root_component=root_component,
            members=ordered,
            predecessors=tuple(predecessors),
            contribution_predecessors=tuple(contribution_predecessors),
            comparison_selections=tuple(comparison_selections),
            representatives=chosen,
            missing_sections=tuple(r for r in sections if r not in roles),
            supported_facets=facets,
            representation=representation,
        ),
    )


def dossier_root(reference, retained) -> LocatedDefinitionComponent:
    """Resolve a provisional sense against the exact selected producer result."""
    selected_ref = RetainedStructuralRef.model_validate(
        reference.model_dump(
            exclude={"component_id", "operation_id", "operation_version", "dependencies"}
        )
    )
    for ref, payload in retained:
        if ref != selected_ref:
            continue
        report = StructuralProductReport.model_validate(payload["report"])
        if (
            report.product_id == ref.product_id
            and report.definition_components is not None
            and report.inputs.dependencies == reference.dependencies
        ):
            for component in report.definition_components.components:
                if component.component_id == reference.component_id:
                    return component
    raise ValueError("dossier root does not resolve in the exact selected predecessor")


def _comparison_member_roles(
    reference,
    report,
    selections,
    relationships,
    root_ref,
    root,
    *,
    require_focus=False,
    applicability_reports=None,
    dossier_passages=None,
):
    comparison = report.comparison
    if comparison is None or comparison.left_reading is None:
        raise ValueError("root binding requires a current retained grouped comparison")
    passages = {p.passage_id: p for p in report.inputs.passages}
    sources = {s.identity: s for s in report.inputs.sources}
    for selection in selections:
        relationship = relationships[selection.relationship_ref]
        decision, edge = relationship["decision"], relationship["edge"]
        side = selection.side
        passage, opposite = (
            (passages[comparison.left_id], passages[comparison.right_id])
            if side == "left"
            else (passages[comparison.right_id], passages[comparison.left_id])
        )
        source = sources[passage.source_ref]
        if (
            edge["relation"] not in {"denotes", "defined-by", "specializes"}
            or decision["scope"] != passage.scope
            or root.scope != passage.scope
            or not passage.effective_version
            or decision.get("effective_version") != passage.effective_version
            or root.effective_version != passage.effective_version
            or relationship["source_view_id"] != source.source_view_id
            or selection.relationship_ref.project_id != source.project_id
            or selection.relationship_ref.release_id != source.release_id
            or root.component_id not in edge["member_target_ids"]
            or not any(
                RetainedComponentRef.model_validate(target["reference"]) == root_ref
                for target in relationship["component_targets"]
            )
        ):
            raise ValueError("comparison side lacks the exact scoped root relationship")
        occurrence = tuple(
            LocatedDefinitionSpan(passage_id=passage.passage_id, **location)
            for location in relationship["located_occurrence"]
        )
        if not occurrence or any(
            not passage.start <= span.start < span.end <= passage.end
            or passage.text[span.start - passage.start : span.end - passage.start] != span.text
            for span in occurrence
        ):
            raise ValueError("relationship occurrence is outside the exact comparison side")
        focus = comparison.left_focus if side == "left" else comparison.right_focus
        if require_focus and focus is None:
            raise ValueError("comparison side has no exact retained reading focus")
        if focus is not None and any(
            not focus.start <= span.start < span.end <= focus.end for span in occurrence
        ):
            raise ValueError("relationship occurrence is outside the exact comparison focus")
        applicability_ref = selection.applicability_ref
        if applicability_ref is not None:
            predecessor = (applicability_reports or {}).get(applicability_ref)
            if predecessor is None or focus is None or predecessor.definition is None:
                raise ValueError("comparison binding lacks its exact applicability predecessor")
            definition = predecessor.definition
            usage = next(
                p for p in predecessor.inputs.passages if p.passage_id == definition.usage_id
            )
            usage_source = next(
                s for s in predecessor.inputs.sources if s.identity == usage.source_ref
            )
            if (
                usage_source != source
                or usage.scope != passage.scope
                or usage.effective_version != passage.effective_version
                or not focus.start <= usage.start < usage.end <= focus.end
                or (usage.start, usage.end) != (occurrence[0].start, occurrence[-1].end)
                or not any(
                    reading.component_ref == root_ref
                    and (
                        reading.link_ref == selection.relationship_ref
                        or edge["relation"] == "specializes"
                    )
                    and reading.outcome in {"applicable_definition", "applicable_explanation"}
                    for reading in definition.readings
                )
            ):
                raise ValueError(
                    "comparison applicability differs from exact focus, root, or relationship"
                )
        applicable = not require_focus or applicability_ref is not None
        conflict = None
        if selection.conflict_passage_id is not None:
            proof = (dossier_passages or {}).get(selection.conflict_passage_id)
            a, b = comparison.left_focus, comparison.right_focus
            if (
                proof is None
                or applicability_ref is None
                or comparison.applicability != "co_applicable"
                or proof.scope != passage.scope
                or proof.effective_version != passage.effective_version
                or a is None
                or b is None
                or a.text == b.text
                or '"' in a.text
                or '"' in b.text
                or proof.text
                not in {
                    f'"{a.text}" contradicts "{b.text}".',
                    f'"{b.text}" contradicts "{a.text}".',
                }
            ):
                raise ValueError(
                    "dossier conflict requires an exact explicit contradiction of both readings"
                )
            conflict = _located(proof, proof.text, 0)
        citation = _located(passage, passage.text, 0)
        binding = DossierComparisonBinding(
            comparison_ref=reference,
            side=side,
            relationship_ref=selection.relationship_ref,
            relationship=edge["relation"],
            root=root_ref,
            source=source,
            citation=citation,
            occurrence=occurrence,
            comparison=comparison,
            opposite_source=sources[opposite.source_ref],
            opposite_citation=_located(opposite, opposite.text, 0),
            applicability_ref=applicability_ref,
            conflict_evidence=conflict,
        )
        if conflict is not None:
            yield "conflict", citation, binding
        if comparison.succession and comparison.succession.newer_id == passage.passage_id:
            yield "revision", comparison.succession.evidence, binding
        exceptions = next(d for d in comparison.dimensions if d.dimension == "exception")
        group = exceptions.left_group if side == "left" else exceptions.right_group
        if (
            applicable
            and edge["relation"] == "specializes"
            and group is not None
            and group.state == "present"
        ):
            for field in group.members:
                for span in field.spans or ():
                    yield "exception", span, binding
        if (
            conflict is None
            and applicable
            and comparison.applicability == "co_applicable"
            and any(d.typed_outcome == "different" for d in comparison.dimensions)
        ):
            yield "variant", citation, binding
        yield "relationship", citation, binding


def derive_dossier_members(
    inputs,
    retained,
    *,
    root=None,
    root_ref=None,
    comparison_selections=(),
    relationships=None,
    require_comparison_focus=False,
):
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
    selections = {}
    for selection in comparison_selections:
        selections.setdefault(selection.comparison_product_id, []).append(selection)
    if selections and (root is None or root_ref is None or relationships is None):
        raise ValueError("comparison bindings require an authenticated dossier root and decisions")
    members = []
    facets = []
    member_ids = set()
    parsed = [
        (ref, payload, StructuralProductReport.model_validate(payload["report"]))
        for ref, payload in retained
    ]
    applicability_reports = {
        ref: report for ref, _, report in parsed if report.kind == "definition_applicability"
    }
    for reference, payload, report in parsed:
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
                if root is not None and c.component_id != root.component_id:
                    continue
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
            readings = tuple(
                reading
                for reading in report.definition.readings
                if root is None or reading.component.component_id == root.component_id
            )
            if not readings:
                continue
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
            for r in readings:
                roles.append(
                    (
                        content_role(r.component.interpretation, r.outcome),
                        r.component.content,
                        None,
                        r.component.interpretation,
                        r.outcome,
                    )
                )
        bound_roles = ()
        selected = selections.pop(report.product_id, ())
        if selected:
            bound_roles = _comparison_member_roles(
                reference,
                report,
                selected,
                relationships,
                root_ref,
                root,
                require_focus=require_comparison_focus,
                applicability_reports=applicability_reports,
                dossier_passages=passages,
            )
        if report.comparison and root is None:
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
            if report.comparison.succession:
                roles.append(("revision", report.comparison.succession.evidence, None, None, None))
        member_roles = (
            *(
                (role, span, component, interpretation, outcome, None)
                for role, span, component, interpretation, outcome in roles
            ),
            *((role, span, None, None, None, binding) for role, span, binding in bound_roles),
        )
        for role, span, component_id, interpretation, outcome, binding in member_roles:
            p = passages[span.passage_id]
            key = sha256(
                canonical_bytes(
                    dict(
                        product=report.product_id,
                        role=role,
                        citation=span.model_dump(mode="json"),
                        **({"sense": root.component_id} if root is not None else {}),
                        **(
                            {"definition_interpretation": interpretation}
                            if interpretation is not None
                            else {}
                        ),
                        **({"applicability_outcome": outcome} if outcome is not None else {}),
                        **(
                            {
                                "comparison_binding": binding.model_dump(
                                    mode="json", exclude_none=True
                                )
                            }
                            if binding is not None
                            else {}
                        ),
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
                sense=root.component_id if root is not None else "unresolved",
                scope=p.scope,
                effective_version=p.effective_version,
                relation_product_id=report.product_id,
                definition_interpretation=interpretation,
                applicability_outcome=outcome,
                comparison_binding=binding,
                qualification="independently_supported"
                if supported and binding is None
                else "proposed",
                assessment_id=supported if binding is None else None,
            )
            if member.member_id in member_ids:
                continue
            member_ids.add(member.member_id)
            members.append(member)
            if supported and (binding is None or role not in {"relationship", "conflict"}):
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
                        assessment_scope="comparison_statement" if binding is not None else None,
                        evidence=(p.passage_id, binding.opposite_citation.passage_id)
                        if binding is not None
                        else (p.passage_id,),
                    )
                )
    if selections:
        raise ValueError("comparison selection lacks its declared retained predecessor")
    return tuple(members), tuple(facets)


class StructuralComparisonConfig(StructuralValue):
    inputs: StructuralInput | None = None
    structural_input_digest: str | None = None
    left_id: str | None = None
    right_id: str | None = None
    left_reading: RetainedContributionRef | None = None
    right_reading: RetainedContributionRef | None = None
    characterization_layers: tuple[dict, ...] = ()

    @model_validator(mode="after")
    def bound_input(self):
        if self.inputs is None:
            if any(
                (
                    self.structural_input_digest,
                    self.left_id,
                    self.right_id,
                    self.left_reading,
                    self.right_reading,
                )
            ):
                raise ValueError("partial comparison config")
        elif (
            self.structural_input_digest != self.inputs.identity
            or not self.characterization_layers
            or self.left_id == self.right_id
            or not {self.left_id, self.right_id} <= {p.passage_id for p in self.inputs.passages}
            or self.left_reading is None
            or self.right_reading is None
            or self.left_reading == self.right_reading
            or not {self.left_reading.contribution_id, self.right_reading.contribution_id}
            <= set(self.inputs.dependencies)
        ):
            raise ValueError("comparison requires exact inputs and two selected passages")
        return self


class StructuralComparisonMethod:
    name = "structure.compare"
    version = "6"
    predicate_version = "6"
    family = MethodFamily.CONSOLIDATE
    unit_type = TaskUnitType.RUN
    tier = MethodTier.DETERMINISTIC
    confidence_source = None
    Config = StructuralComparisonConfig
    resources = Resources()

    __selection_operation__: ClassVar[dict[str, Any]] = {
        "id": "structure.compare/selection",
        "profile": "selection",
        "subject": "authored-structural-input",
        "context": ["project", "original-source", "frozen-source-set", "frozen-selection"],
        "roles": [
            {
                "name": "left_passage",
                "kind": "https://corpus-structure.dev/semantic/data-operation-consumers/DdoPassageBinding",
                "direction": "input",
                "minimum": 1,
                "maximum": 1,
                "collection": "scalar",
                "presence": "required",
                "support": {
                    "provenance": "exact",
                    "source": "frozen-source-set",
                    "coverage": "qualified-selected-population",
                    "identity_requirements": ["episode"],
                    "source_set": "structural-input-sources",
                    "source_reference_field": "source_ref",
                },
                "subject_field": "input_subject",
            },
            {
                "name": "right_passage",
                "kind": "https://corpus-structure.dev/semantic/data-operation-consumers/DdoPassageBinding",
                "direction": "input",
                "minimum": 1,
                "maximum": 1,
                "collection": "scalar",
                "presence": "required",
                "support": {
                    "provenance": "exact",
                    "source": "frozen-source-set",
                    "coverage": "qualified-selected-population",
                    "identity_requirements": ["episode"],
                    "source_set": "structural-input-sources",
                    "source_reference_field": "source_ref",
                },
                "subject_field": "input_subject",
            },
            {
                "name": "left_reading",
                "kind": "https://corpus-structure.dev/semantic/data-operation-consumers/DdoReadingBinding",
                "direction": "input",
                "minimum": 1,
                "maximum": 1,
                "collection": "scalar",
                "presence": "required",
                "support": {
                    "provenance": "exact",
                    "source": "frozen-source-set",
                    "coverage": "qualified-selected-population",
                    "identity_requirements": ["episode"],
                    "source_set": "structural-input-sources",
                    "source_reference_field": "source_ref",
                },
                "subject_field": "input_subject",
            },
            {
                "name": "right_reading",
                "kind": "https://corpus-structure.dev/semantic/data-operation-consumers/DdoReadingBinding",
                "direction": "input",
                "minimum": 1,
                "maximum": 1,
                "collection": "scalar",
                "presence": "required",
                "support": {
                    "provenance": "exact",
                    "source": "frozen-source-set",
                    "coverage": "qualified-selected-population",
                    "identity_requirements": ["episode"],
                    "source_set": "structural-input-sources",
                    "source_reference_field": "source_ref",
                },
                "subject_field": "input_subject",
            },
        ],
        "applicability": ["admitted-selected-populations"],
        "invariants": ["original-subject-and-source-preserved"],
        "coverage": "qualified-selected-population",
        "outcomes": ["selected", "unavailable", "invalid"],
        "precision": "exact",
        "dependencies": [],
        "effects": [],
        "capabilities": {
            "forms": ["scalar"],
            "preparation": "none",
            "cancellation": "call-boundary",
            "ownership": "immutable-selection",
        },
        "behavior": "retained-binding-selection-v1",
        "parameters": {
            "left_passage_id": {"value_type": "string"},
            "right_passage_id": {"value_type": "string"},
            "left_reading_id": {"value_type": "string"},
            "right_reading_id": {"value_type": "string"},
        },
        "binding": {
            "operator": "all",
            "children": [
                {
                    "operator": "equal",
                    "operands": [
                        {
                            "kind": "field",
                            "value_type": "DdoBindingText",
                            "field": {
                                "role": "left_reading",
                                "projection": "https://corpus-structure.dev/semantic/data-operation-consumers/DdoReadingBinding",
                                "field": "passage_id",
                            },
                        },
                        {
                            "kind": "field",
                            "value_type": "DdoBindingText",
                            "field": {
                                "role": "left_passage",
                                "projection": "https://corpus-structure.dev/semantic/data-operation-consumers/DdoPassageBinding",
                                "field": "passage_id",
                            },
                        },
                    ],
                },
                {
                    "operator": "forall",
                    "roles": ["left_reading"],
                    "population": "selected-left-reading",
                    "children": [
                        {
                            "operator": "equal",
                            "operands": [
                                {
                                    "kind": "field",
                                    "value_type": "DdoBindingText",
                                    "field": {
                                        "role": "left_reading",
                                        "projection": "https://corpus-structure.dev/semantic/data-operation-consumers/DdoReadingBinding",
                                        "field": "contribution_id",
                                    },
                                },
                                {
                                    "kind": "parameter",
                                    "name": "left_reading_id",
                                    "value_type": "DdoBindingText",
                                },
                            ],
                        }
                    ],
                },
                {
                    "operator": "equal",
                    "operands": [
                        {
                            "kind": "field",
                            "value_type": "DdoBindingText",
                            "field": {
                                "role": "right_reading",
                                "projection": "https://corpus-structure.dev/semantic/data-operation-consumers/DdoReadingBinding",
                                "field": "passage_id",
                            },
                        },
                        {
                            "kind": "field",
                            "value_type": "DdoBindingText",
                            "field": {
                                "role": "right_passage",
                                "projection": "https://corpus-structure.dev/semantic/data-operation-consumers/DdoPassageBinding",
                                "field": "passage_id",
                            },
                        },
                    ],
                },
                {
                    "operator": "forall",
                    "roles": ["right_reading"],
                    "population": "selected-right-reading",
                    "children": [
                        {
                            "operator": "equal",
                            "operands": [
                                {
                                    "kind": "field",
                                    "value_type": "DdoBindingText",
                                    "field": {
                                        "role": "right_reading",
                                        "projection": "https://corpus-structure.dev/semantic/data-operation-consumers/DdoReadingBinding",
                                        "field": "contribution_id",
                                    },
                                },
                                {
                                    "kind": "parameter",
                                    "name": "right_reading_id",
                                    "value_type": "DdoBindingText",
                                },
                            ],
                        }
                    ],
                },
                {"operator": "distinct", "roles": ["left_passage", "right_passage"]},
                {"operator": "distinct", "roles": ["left_reading", "right_reading"]},
                {
                    "operator": "forall",
                    "roles": ["left_passage"],
                    "population": "selected-left-passage",
                    "children": [
                        {
                            "operator": "equal",
                            "operands": [
                                {
                                    "kind": "field",
                                    "value_type": "DdoBindingText",
                                    "field": {
                                        "role": "left_passage",
                                        "projection": "https://corpus-structure.dev/semantic/data-operation-consumers/DdoPassageBinding",
                                        "field": "passage_id",
                                    },
                                },
                                {
                                    "kind": "parameter",
                                    "name": "left_passage_id",
                                    "value_type": "DdoBindingText",
                                },
                            ],
                        }
                    ],
                },
                {
                    "operator": "forall",
                    "roles": ["right_passage"],
                    "population": "selected-right-passage",
                    "children": [
                        {
                            "operator": "equal",
                            "operands": [
                                {
                                    "kind": "field",
                                    "value_type": "DdoBindingText",
                                    "field": {
                                        "role": "right_passage",
                                        "projection": "https://corpus-structure.dev/semantic/data-operation-consumers/DdoPassageBinding",
                                        "field": "passage_id",
                                    },
                                },
                                {
                                    "kind": "parameter",
                                    "name": "right_passage_id",
                                    "value_type": "DdoBindingText",
                                },
                            ],
                        }
                    ],
                },
            ],
        },
    }

    def select_bound(self, binding: BindingResult) -> BoundConsumerSelection:
        """Consume the target operation's retained relational selection unchanged."""
        return BoundConsumerSelection.from_binding(
            binding, operation=self.__selection_operation__["id"]
        )

    def select_bound_native(self, connection, model, binding, *, demand_id,
                            read_id, trust_snapshot, max_bytes):
        from corpus_structure.semantic.data_operation_consumers import hydrate_consumer_selection
        selected = self.select_bound(binding)
        hydrated = hydrate_consumer_selection(
            connection, model, selected, demand_id=demand_id, read_id=read_id,
            trust_snapshot=trust_snapshot, max_bytes=max_bytes,
        )
        return self.select_hydrated(hydrated)

    def select_hydrated(self, inputs):
        self.select_bound(inputs.selection.binding)
        left = (inputs.one("left_passage"), inputs.one("left_reading"))
        right = (inputs.one("right_passage"), inputs.one("right_reading"))
        if left[0].value()["passage_id"] == right[0].value()["passage_id"]:
            raise ValueError("structural comparison requires distinct selected passages")
        for passage, reading in (left, right):
            if (passage.value()["passage_id"], passage.value()["source_ref"]) != (
                reading.value()["passage_id"], reading.value()["source_ref"]
            ):
                raise ValueError("selected structural reading differs from its passage")
        return left, right

    def select(self, run, cfg) -> tuple[UnitRef, ...]:
        return (UnitRef(TaskUnitType.RUN, unit_key=cfg.inputs.identity),) if cfg.inputs else ()

    def input_digest(self, unit, cfg):
        from corpus_structure.semantic.identity import canonical_bytes

        return Digest(canonical_bytes(cfg.model_dump(mode="json")))

    def run(self, units, cfg, ctx):
        if cfg.inputs is None or cfg.left_reading is None or cfg.right_reading is None:
            raise ValueError("comparison inputs absent")
        ctx.check_active()
        ctx.reader.validate_structural_inputs(cfg.inputs)
        primary = {}
        for source in cfg.inputs.sources:
            primary.update(
                ctx.reader.primary_characterization(
                    source.source_view_id, families=("formal.lexical", "formal.threshold")
                )
            )
        passages = {p.passage_id: p for p in cfg.inputs.passages}
        sources = {source.identity: source for source in cfg.inputs.sources}

        def side(passage_id, reference):
            ctx.check_active()
            passage = passages[passage_id]
            return read_retained_clause(
                passage,
                sources[passage.source_ref],
                reference,
                ctx.reader.retained_source_contribution(reference),
                predicate_version=self.predicate_version,
                primary_layers=primary,
            )

        report = compare_clauses(
            cfg.inputs,
            left=side(cfg.left_id, cfg.left_reading),
            right=side(cfg.right_id, cfg.right_reading),
            left_reading=cfg.left_reading,
            right_reading=cfg.right_reading,
            typed_groups=True,
            primary_layers=primary,
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
    root_component: RetainedComponentRef | None = None
    predecessors: tuple[RetainedStructuralRef, ...] = ()
    contribution_predecessors: tuple[RetainedContributionRef, ...] = ()
    comparison_selections: tuple[DossierComparisonSelection, ...] = Field(
        default=(), exclude_if=lambda value: not value
    )
    member_budget: int = Field(default=12, gt=0, strict=True)
    policy: Literal["supported-facet-greedy-1", "source-order-control-1"] = (
        "supported-facet-greedy-1"
    )

    @model_validator(mode="after")
    def bound_input(self):
        if self.inputs is None:
            if (
                self.structural_input_digest
                or self.root_component
                or self.predecessors
                or self.contribution_predecessors
                or self.comparison_selections
            ):
                raise ValueError("partial dossier config")
        elif (
            self.structural_input_digest != self.inputs.identity
            or self.root_component is None
            or not any(p.product_id == self.root_component.product_id for p in self.predecessors)
        ):
            raise ValueError("dossier requires original inputs and retained predecessors")
        if len({p.product_id for p in self.predecessors}) != len(self.predecessors):
            raise ValueError("duplicate dossier predecessor")
        if len({p.contribution_id for p in self.contribution_predecessors}) != len(
            self.contribution_predecessors
        ):
            raise ValueError("duplicate dossier contribution predecessor")
        if len(set(self.comparison_selections)) != len(self.comparison_selections) or any(
            selection.comparison_product_id not in {ref.product_id for ref in self.predecessors}
            or self.inputs is None
            or selection.relationship_ref.edge_id not in self.inputs.dependencies
            or (
                selection.applicability_ref is not None
                and selection.applicability_ref not in self.predecessors
            )
            for selection in self.comparison_selections
        ):
            raise ValueError("dossier comparison binding requires exact declared dependencies")
        return self


class StructuralDossierMethod:
    name = "structure.dossier"
    version = "3"
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
        if cfg.inputs is None or cfg.root_component is None:
            raise ValueError("dossier inputs absent")
        retained = []
        for reference in cfg.predecessors:
            ctx.check_active()
            retained.append((reference, ctx.reader.retained_structural_report(reference)))
        root = dossier_root(cfg.root_component, retained)
        checked = ctx.reader.resolve_definition_component(cfg.root_component)
        if LocatedDefinitionComponent.model_validate(checked) != root:
            raise ValueError("dossier root differs from its native component")
        relationships = {}
        for selection in cfg.comparison_selections:
            reference = selection.relationship_ref
            if reference not in relationships:
                ctx.check_active()
                relationships[reference] = ctx.reader.retained_relationship_decision(reference)
        members, facets = derive_dossier_members(
            cfg.inputs,
            retained,
            root=root,
            root_ref=cfg.root_component,
            comparison_selections=cfg.comparison_selections,
            relationships=relationships,
            require_comparison_focus=True,
        )
        from .dossier_contributions import derive_contribution_members

        source_members = []
        for reference in cfg.contribution_predecessors:
            ctx.check_active()
            payload = ctx.reader.retained_source_contribution(reference)
            source_members.extend(
                derive_contribution_members(cfg.inputs, reference, payload, root=root)
            )
        members = (*members, *source_members)
        report = select_dossier(
            cfg.inputs,
            root_id=root.component_id,
            root_component=cfg.root_component,
            members=members,
            supported_facets=facets,
            predecessors=cfg.predecessors,
            contribution_predecessors=cfg.contribution_predecessors,
            comparison_selections=cfg.comparison_selections,
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


class ConditionQualificationConfig(StructuralValue):
    inputs: StructuralInput | None = None
    structural_input_digest: str | None = None
    attachment: RetainedContributionRef | None = None

    @model_validator(mode="after")
    def selected_input(self):
        if self.inputs is None:
            if self.structural_input_digest is not None or self.attachment is not None:
                raise ValueError("condition qualification requires complete source and attachment")
        elif self.structural_input_digest != self.inputs.identity or self.attachment is None:
            raise ValueError("condition qualification requires complete source and attachment")
        return self


def condition_qualification(inputs, attachment, retained):
    """Project only the condition and the declared host predicate, under retained custody."""
    from corpus_structure.semantic.observations import source_python
    from corpus_structure.semantic.structural_products import (
        ConditionQualificationProduct,
        ConditionRoleCitation,
    )

    rows = {row["contribution_id"]: row for row in retained["contributions"]}
    relation = rows.get(attachment.contribution_id)
    if (
        relation is None
        or relation.get("semantic_type") != "structural.predicate_qualification"
        or relation.get("kind") != "relation"
    ):
        raise ValueError("condition statement requires the exact directed qualification")
    component = relation["component"]
    qualifier_id, host_id = (
        component["qualifier_contribution_id"],
        component["host_contribution_id"],
    )
    version = component["question_version"]
    effective = component.get("effective_version")
    relation_kind = component["qualifier_kind"]
    if (
        component["kind"] != "predicate_qualifier"
        or component["question"] != "source_predicate_interpretation"
        or version != "6"
        or relation_kind not in {"condition", "assumption"}
        or component["scope"] != inputs.scope
        or tuple((e["role"], e["contribution_id"]) for e in relation["endpoints"])
        != (("qualifier", qualifier_id), ("host", host_id))
    ):
        raise ValueError("condition statement requires the exact directed qualification")
    if qualifier_id not in rows or host_id not in rows:
        raise ValueError("condition statement lacks the retained endpoint closure")
    cue, host = rows[qualifier_id], rows[host_id]
    for row, kind in ((cue, "predicate_cue"), (host, "predicate_frame")):
        value = row["component"]
        if (
            row["semantic_type"] != f"structural.{kind}"
            or row["pin"] != relation["pin"]
            or value["kind"] != kind
            or value["question"] != "source_predicate_frames"
            or value["question_version"] != version
            or value["scope"] != inputs.scope
            or value.get("effective_version") != effective
            or row["contribution_id"] not in relation["members"]
        ):
            raise ValueError("condition statement differs from the retained endpoint scope")
    cue_part, host_part = cue["component"], host["component"]
    cross_hosts = cue_part.get("cross_block_hosts")
    unique_host = (
        tuple(cross_hosts) == (host_id,)
        if cross_hosts
        else (
            tuple(cue_part.get("candidate_tokens", ())) == (host_part["predicate_token"],)
            and cue_part["block"] == host_part["block"]
            and cue_part["annotation"] == host_part["annotation"]
        )
    )
    if (
        cue_part["cue_kind"] != relation_kind
        or cue_part["host_state"] != "located"
        or not unique_host
    ):
        raise ValueError("condition statement requires a uniquely located host")
    (predicate,) = (entry for entry in host_part["frame_members"] if entry["role"] == "predicate")
    member = rows.get(predicate["contribution"])
    if (
        member is None
        or predicate["outcome"] != "complete"
        or member["semantic_type"] != "structural.predicate_member"
        or member["contribution_id"] not in host["members"]
        or member["pin"] != relation["pin"]
        or source_python(member["value"])["role"] != "predicate"
    ):
        raise ValueError("condition host requires its complete declared predicate member")

    pin = relation["pin"]
    (source,) = (
        source
        for source in inputs.sources
        if source.project_id == attachment.project_id
        and source.source_view_id == pin["source_view_id"]
        and source.native_task_id == pin["native_product_task_id"]
        and source.native_product_key == pin["product_key"]
        and source.native_content_digest == pin["product_digest"]
        and source.projection_digest == pin["projection_digest"]
        and source.recipe_digest == pin["recipe_digest"]
    )
    (projection,) = (row["projection"] for row in retained["sources"] if row["pin"] == pin)

    def locations(row):
        locations = []
        for anchor in row["anchors"]:
            if (
                anchor["pin"] != pin
                or anchor["space"] != "native"
                or anchor["precision"] != "exact"
            ):
                raise ValueError("condition role requires exact original source anchors")
            pointer = anchor["pointer"]
            (piece,) = (
                piece
                for piece in projection["pieces"]
                if piece["kind"] == "native_text"
                and piece["item_ref"]
                + (
                    f"/data/table_cells/{piece['cell_index']}"
                    if piece.get("cell_index") is not None
                    else ""
                )
                == pointer
            )
            start, end = piece["start"] + anchor["start"], piece["start"] + anchor["end"]
            if not piece["start"] <= start < end <= piece["end"]:
                raise ValueError("condition role exceeds its original source item")
            (passage,) = (
                p
                for p in inputs.passages
                if p.source_ref == source.identity
                and p.scope == inputs.scope
                and p.effective_version == effective
                and p.start <= start < end <= p.end
            )
            text = passage.text[start - passage.start : end - passage.start]
            if text != anchor["source_piece"] or projection["text"][start:end] != text:
                raise ValueError("condition role differs from the original source text")
            locations.append(
                ConditionRoleCitation(
                    source_pointer=pointer,
                    span=LocatedDefinitionSpan(
                        passage_id=passage.passage_id, start=start, end=end, text=text
                    ),
                )
            )
        return tuple(locations)

    return ConditionQualificationProduct(
        relation=relation_kind,
        attachment=attachment,
        effective_version=effective,
        qualifier=locations(cue),
        host_predicate=locations(member),
    )


class ConditionQualificationMethod:
    name = "structure.condition_qualification"
    version = "1"
    family = MethodFamily.RESOLVE
    unit_type = TaskUnitType.RUN
    tier = MethodTier.DETERMINISTIC
    confidence_source = None
    Config = ConditionQualificationConfig
    resources = Resources(worker="cpu", batch_size=1, max_concurrency=1)

    def select(self, run, cfg):
        if cfg.inputs is None or cfg.attachment is None:
            return ()
        digest = sha256(canonical_bytes(cfg.attachment.model_dump(mode="json"))).hexdigest()
        return (UnitRef(TaskUnitType.RUN, unit_key="condition-qualification:" + digest),)

    def input_digest(self, unit, cfg):
        return Digest(canonical_bytes(cfg.model_dump(mode="json", exclude_none=True)))

    def run(self, units, cfg, ctx):
        if cfg.inputs is None or cfg.attachment is None:
            raise ValueError("condition qualification requires complete source and attachment")
        ctx.check_active()
        ctx.reader.validate_structural_inputs(cfg.inputs)
        if cfg.attachment.release_id != ctx.reader.prepared.release_id:
            raise ValueError("condition attachment belongs to another release")
        retained = ctx.reader.retained_source_contribution(cfg.attachment)
        report = StructuralProductReport(
            kind="condition_qualification",
            inputs=cfg.inputs,
            condition_qualification=condition_qualification(cfg.inputs, cfg.attachment, retained),
        )
        return tuple(
            UnitResult(
                ref=unit.ref,
                outcome=ObservationOutcome.PRODUCED,
                structural_product=report.model_dump(mode="json", exclude_none=True),
            )
            for unit in units
        )
