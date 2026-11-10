"""Exact review populations and pre-hydration source-record selectors."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import and_, exists, func, select, tuple_

from .metadata import table
from .refusals import SemanticRefusal


class TerminologySelection(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    review_run_id: int = Field(strict=True, ge=1)
    review_cut_id: int = Field(strict=True, ge=1)
    vocabulary_release: str
    field: str
    value: str | None = None
    outcome: str = "selected"
    mapping_predicate: str | None = None
    contribution_ids: tuple[str, ...] | None = None


def review_population(conn, *, run_id: int, cut_id: int):
    completed, run, cut, member, task = (
        table(n)
        for n in ("ops.completed_result", "ops.run", "ops.input_cut", "ops.cut_task", "ops.task")
    )
    row = conn.execute(
        select(run.c.project_id, run.c.release_id)
        .join(completed, completed.c.run_id == run.c.id)
        .join(cut, cut.c.id == completed.c.cut_id)
        .where(
            run.c.id == run_id,
            completed.c.cut_id == cut_id,
            run.c.sealed,
            run.c.status == "finished",
            cut.c.final,
        )
    ).one_or_none()
    if row is None:
        raise SemanticRefusal("review population requires its immutable completed final result")
    tasks = (
        select(func.coalesce(task.c.reused_task_id, task.c.id))
        .join(member, member.c.task_id == task.c.id)
        .where(
            task.c.run_id == run_id,
            member.c.cut_id == cut_id,
            task.c.status.in_(("done", "empty", "reused")),
        )
    )
    return row, tasks


def terminology_selector(
    conn,
    selection: TerminologySelection,
    *,
    source_run_id,
    source_cut_id,
    release_id,
    realization_id,
    project_id,
    roots,
    selected_roots,
):
    from .interpretations import FIELD_ENUMS, MAPPINGS

    if (
        selection.field not in FIELD_ENUMS
        or selection.outcome not in {"selected", "unresolved", "no_match"}
        or (selection.mapping_predicate is not None and selection.mapping_predicate not in MAPPINGS)
    ):
        raise SemanticRefusal("unsupported terminology selection")
    review, tasks = review_population(
        conn, run_id=selection.review_run_id, cut_id=selection.review_cut_id
    )
    if review.project_id != project_id:
        raise SemanticRefusal("review and source populations belong to different projects")
    index = table("kb.terminology_interpretation_field")
    predicates = [
        index.c.task_id.in_(tasks),
        index.c.source_run_id == source_run_id,
        index.c.source_cut_id == source_cut_id,
        index.c.source_release_id == release_id,
        index.c.realization_id == realization_id,
        index.c.field == selection.field,
        index.c.vocabulary_release == selection.vocabulary_release,
        index.c.outcome == selection.outcome,
    ]
    if selection.value is not None:
        predicates.append(index.c.selected_value == selection.value)
    if selection.mapping_predicate is not None:
        predicates.append(index.c.mapping_predicate == selection.mapping_predicate)
    if selection.contribution_ids is not None:
        if not selection.contribution_ids or len(set(selection.contribution_ids)) != len(
            selection.contribution_ids
        ):
            raise SemanticRefusal("review decision selection must be nonempty and unique")
        predicates.append(index.c.contribution_id.in_(selection.contribution_ids))
    # Ambiguity is checked over the selected review population before category filtering:
    # choosing a value cannot hide a conflicting review of the same source field.
    scope = [
        *predicates[:7],
        tuple_(index.c.record_id, index.c.interpretation_id).in_(selected_roots),
    ]
    if selection.contribution_ids is not None:
        scope.append(index.c.contribution_id.in_(selection.contribution_ids))
    ambiguous = (
        select(index.c.record_id, index.c.interpretation_id)
        .where(*scope)
        .group_by(index.c.record_id, index.c.interpretation_id)
        .having(func.count() > 1)
        .limit(1)
    )
    if conn.execute(ambiguous).first() is not None:
        raise SemanticRefusal("multiple field reviews require explicit contribution selection")
    return exists(
        select(1).where(
            *predicates,
            index.c.record_id == roots.c.record_id,
            index.c.interpretation_id == roots.c.interpretation_id,
        )
    )


def collect_interpretation_uses(
    conn,
    *,
    source_run_id: int,
    review_run_id: int,
    review_cut_id: int,
    vocabulary_release: str,
    enum: str | None = None,
    member: str | None = None,
    after: tuple[int, str, str] | None = None,
    limit: int = 100,
) -> dict:
    """Bounded surveyed uses; continuation covers these two immutable populations only."""
    from sqlalchemy import tuple_

    from .interpretations import FIELD_ENUMS

    if not 1 <= limit <= 1000:
        raise SemanticRefusal("use survey limit outside supported range")
    completed, run, realization = (
        table(n) for n in ("ops.completed_result", "ops.run", "data.realization")
    )
    source = (
        conn.execute(
            select(completed, run.c.project_id, realization.c.data_revision)
            .join(run, run.c.id == completed.c.run_id)
            .join(
                realization,
                and_(
                    realization.c.release_id == completed.c.release_id,
                    realization.c.realization_id == completed.c.output_realization_id,
                ),
            )
            .where(completed.c.run_id == source_run_id, run.c.sealed, run.c.status == "finished")
        )
        .mappings()
        .one_or_none()
    )
    if source is None:
        raise SemanticRefusal("use survey source result is unavailable")
    review, tasks = review_population(conn, run_id=review_run_id, cut_id=review_cut_id)
    if source["project_id"] != review.project_id:
        raise SemanticRefusal("use survey projects differ")
    from sqlalchemy import case, cast, literal, union_all

    term = table("kb.terminology_interpretation_field")
    measurement = table("kb.measurement_interpretation")
    common = tuple(
        column.key
        for column in term.c
        if column.key
        not in {"field", "selected_value", "meaning", "mapping_predicate", "mapping_direction"}
    )

    def population(index):
        return (
            index.c.task_id.in_(tasks),
            index.c.source_run_id == source_run_id,
            index.c.source_cut_id == source["cut_id"],
            index.c.source_release_id == source["release_id"],
            index.c.realization_id == source["output_realization_id"],
            index.c.data_revision == source["data_revision"],
            index.c.vocabulary_release == vocabulary_release,
        )

    branches = [
        select(
            *[term.c[k] for k in common],
            term.c.field,
            term.c.selected_value,
            term.c.meaning,
            term.c.mapping_predicate,
            term.c.mapping_direction,
            literal("terminology.interpretation").label("semantic_type"),
            case(FIELD_ENUMS, value=term.c.field).label("enum"),
        ).where(*population(term))
    ]
    for field, enum_name in (
        ("unit", "RecognizedTimeUnit"),
        ("quantity_kind", "RecognizedQuantityKind"),
    ):
        branches.append(
            select(
                *[measurement.c[k] for k in common],
                literal(field).label("field"),
                measurement.c[field].label("selected_value"),
                *[
                    cast(None, term.c[k].type).label(k)
                    for k in ("meaning", "mapping_predicate", "mapping_direction")
                ],
                literal("measurement.interpretation").label("semantic_type"),
                literal(enum_name).label("enum"),
            ).where(*population(measurement))
        )
    index = union_all(*branches).subquery("bound_interpretation_uses")
    statement = select(index)
    if enum is not None:
        statement = statement.where(index.c.enum == enum)
    if member is not None:
        statement = statement.where(index.c.selected_value == member)
    if after is not None:
        statement = statement.where(
            tuple_(index.c.task_id, index.c.contribution_id, index.c.field) > after
        )
    rows = (
        conn.execute(
            statement.order_by(index.c.task_id, index.c.contribution_id, index.c.field).limit(
                limit + 1
            )
        )
        .mappings()
        .all()
    )
    more = len(rows) > limit
    rows = rows[:limit]
    return dict(
        source_run_id=source_run_id,
        source_cut_id=source["cut_id"],
        source_release_id=source["release_id"],
        realization_id=source["output_realization_id"],
        data_revision=source["data_revision"],
        review_run_id=review_run_id,
        review_cut_id=review_cut_id,
        vocabulary_release=vocabulary_release,
        enum=enum,
        member=member,
        items=[{str(key): value for key, value in row.items()} for row in rows],
        complete=not more,
        next_after=[rows[-1][k] for k in ("task_id", "contribution_id", "field")] if more else None,
        coverage="selected_source_and_review_results_only",
    )


def measurement_groups(
    conn, *, source_run_id: int, review_run_id: int, review_cut_id: int, limit=100
) -> dict:
    """Group attributed identifiers; no numerical equivalence or source completeness claim."""
    review, tasks = review_population(conn, run_id=review_run_id, cut_id=review_cut_id)
    completed, run = table("ops.completed_result"), table("ops.run")
    source = (
        conn.execute(
            select(completed, run.c.project_id)
            .join(run, run.c.id == completed.c.run_id)
            .where(completed.c.run_id == source_run_id, run.c.status == "finished", run.c.sealed)
        )
        .mappings()
        .one_or_none()
    )
    if source is None or source["project_id"] != review.project_id:
        raise SemanticRefusal("measurement populations differ or are unavailable")
    if not 1 <= limit <= 1000:
        raise SemanticRefusal("measurement group limit outside supported range")
    index = table("kb.measurement_interpretation")
    statement = (
        select(
            index.c.unit,
            index.c.quantity_kind,
            index.c.basis_status,
            index.c.basis,
            index.c.outcome,
            func.count().label("interpretations"),
        )
        .where(
            index.c.task_id.in_(tasks),
            index.c.source_run_id == source_run_id,
            index.c.source_cut_id == source["cut_id"],
            index.c.source_release_id == source["release_id"],
            index.c.realization_id == source["output_realization_id"],
        )
        .group_by(
            index.c.unit,
            index.c.quantity_kind,
            index.c.basis_status,
            index.c.basis,
            index.c.outcome,
        )
        .order_by(
            index.c.unit,
            index.c.quantity_kind,
            index.c.basis_status,
            index.c.basis,
            index.c.outcome,
        )
    )
    rows = conn.execute(statement.limit(limit + 1)).mappings().all()
    groups = [dict(r) for r in rows[:limit]]
    from sqlalchemy import or_

    dimensions = ("unit", "quantity_kind", "basis_status", "basis", "outcome")
    if groups:
        selected_groups = or_(
            *(
                and_(
                    *(
                        index.c[k].is_(None) if g[k] is None else index.c[k] == g[k]
                        for k in dimensions
                    )
                )
                for g in groups
            )
        )
        ranked = (
            select(
                index,
                func.row_number()
                .over(
                    partition_by=[index.c[k] for k in dimensions],
                    order_by=[index.c.task_id, index.c.contribution_id],
                )
                .label("ordinal"),
            )
            .where(
                index.c.task_id.in_(tasks),
                index.c.source_run_id == source_run_id,
                index.c.source_cut_id == source["cut_id"],
                index.c.source_release_id == source["release_id"],
                index.c.realization_id == source["output_realization_id"],
                selected_groups,
            )
            .subquery()
        )
        members = conn.execute(select(ranked).where(ranked.c.ordinal <= 20)).mappings().all()
        for group in groups:
            group["members"] = [
                {
                    k: r[k]
                    for k in (
                        "task_id",
                        "contribution_id",
                        "record_id",
                        "interpretation_id",
                        "source_release_id",
                        "realization_id",
                        "data_revision",
                        "vocabulary_release",
                        "metadata_digest",
                    )
                }
                for r in members
                if all(r[k] == group[k] for k in dimensions)
            ]
            group["members_complete"] = group["interpretations"] <= 20
            group["actual_quantity_compatibility"] = (
                "unassessed; original referent, role and source evidence "
                "remain in referenced records"
            )
    return dict(
        source_run_id=source_run_id,
        source_cut_id=source["cut_id"],
        review_run_id=review_run_id,
        review_cut_id=review_cut_id,
        groups=groups,
        complete=len(rows) <= limit,
        numerical_equivalence="unassessed",
        coverage="retained_review_population_only",
    )


def terminology_matches(conn, selection, *, source_run_id, source_cut_id, record_keys):
    from sqlalchemy import tuple_

    if not record_keys:
        return ()
    _, tasks = review_population(
        conn, run_id=selection.review_run_id, cut_id=selection.review_cut_id
    )
    index = table("kb.terminology_interpretation_field")
    predicates = [
        index.c.task_id.in_(tasks),
        index.c.source_run_id == source_run_id,
        index.c.source_cut_id == source_cut_id,
        index.c.field == selection.field,
        index.c.vocabulary_release == selection.vocabulary_release,
        index.c.outcome == selection.outcome,
        tuple_(index.c.record_id, index.c.interpretation_id).in_(record_keys),
    ]
    if selection.value is not None:
        predicates.append(index.c.selected_value == selection.value)
    if selection.mapping_predicate is not None:
        predicates.append(index.c.mapping_predicate == selection.mapping_predicate)
    if selection.contribution_ids is not None:
        predicates.append(index.c.contribution_id.in_(selection.contribution_ids))
    return tuple(
        dict(r, review_run_id=selection.review_run_id, review_cut_id=selection.review_cut_id)
        for r in conn.execute(
            select(index).where(*predicates).order_by(index.c.task_id, index.c.contribution_id)
        ).mappings()
    )
