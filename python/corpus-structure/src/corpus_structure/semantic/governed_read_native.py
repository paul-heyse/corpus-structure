"""Native governed-selection acquisition and exact settled-cut custody."""

from sqlalchemy import Text, and_, cast, column, func, literal, select
from sqlalchemy.dialects.postgresql import JSONB, insert

from corpus_structure.schema.integrity import role_name

from .demand_registration_native import _clock, _json, _refusal, _xid
from .native_objects import NativeProgramAccess
from .native_program import (
    Assign,
    Block,
    If,
    Local,
    NativeRoutine,
    Parameter,
    Perform,
    Return,
    SelectInto,
    core_variable,
    pg_type,
)
from .native_program_registry import ProgramDeclaration


def governed_read_program(model):
    selections = model.tables["ops.data_demand_selection"]
    reads = model.tables["ops.data_demand_read"]
    settled = model.tables["ops.data_selection_settled_read"]
    p = core_variable("p_payload", JSONB())
    scope = func.coalesce(p["scope"], _json("{}"))
    head = core_variable("head", JSONB())
    context = core_variable("acquired", JSONB())
    observation = core_variable("observation", JSONB())
    status = core_variable("freshness", Text())
    selected_read = core_variable("selected_read", Text())
    last = func.coalesce(p["mode"].astext, "current") == "last-settled"
    retained = settled.alias("retained")
    named = and_(
        selections.c.project_id == p["project_id"].astext,
        selections.c.name == p["selection_name"].astext,
    )
    selected = select(func.to_jsonb(selections.table_valued())).where(named)
    continued = reads.alias("continued")
    selected_head = selected.order_by(selections.c.generation.desc()).limit(1)
    continued_head = (
        selected.join(continued, continued.c.demand_id == selections.c.demand_id)
        .where(
            continued.c.id == p["read_id"].astext,
            selections.c.generation
            == cast(p["selection_generation"].astext, selections.c.generation.type),
        )
        .order_by(selections.c.generation.desc())
        .limit(1)
    )
    retained_head = (
        selected.join(
            retained,
            and_(
                retained.c.project_id == selections.c.project_id,
                retained.c.name == selections.c.name,
                retained.c.generation == selections.c.generation,
            ),
        )
        .where(retained.c.scope == scope)
        .order_by(
            selections.c.generation.desc(), retained.c.created_at.desc(), retained.c.read_id.desc()
        )
        .limit(1)
    )
    summary_rows = (
        func.jsonb_array_elements(observation["payload"]["selections"])
        .table_valued(column("value", JSONB()))
        .alias("governed_observation")
    )
    summary = (
        select(summary_rows.c.value)
        .where(summary_rows.c.value.op("->>")("selection_name") == p["selection_name"].astext)
        .scalar_subquery()
    )
    # The public record deliberately excludes scheduler counts and undisclosed work.
    result = func.jsonb_build_object(
        "selection_name",
        p["selection_name"],
        "selection_generation",
        head["generation"],
        "state",
        status,
        "last_settled",
        last,
        "demand_id",
        head["demand_id"],
        "read_id",
        selected_read,
    )
    routine = NativeRoutine(
        "ops",
        "read_governed_selection",
        (Parameter("p_payload", pg_type("jsonb")),),
        pg_type("jsonb"),
        Block(
            (
                _refusal(
                    func.coalesce(p["mode"].astext, "current").not_in(("current", "last-settled")),
                    "invalid governed read mode",
                    "22023",
                ),
                If(
                    p.has_key("read_id"),
                    (
                        _refusal(
                            ~p.has_key("selection_generation"),
                            "governed continuation requires its selection generation",
                            "22023",
                        ),
                        SelectInto(continued_head, ("head",), strict=True),
                        Assign("selected_read", p["read_id"].astext),
                    ),
                    (
                        If(
                            last,
                            (
                                SelectInto(retained_head, ("head",)),
                                SelectInto(
                                    select(retained.c.read_id)
                                    .where(
                                        retained.c.project_id == p["project_id"].astext,
                                        retained.c.name == p["selection_name"].astext,
                                        retained.c.generation
                                        == cast(
                                            head["generation"].astext, selections.c.generation.type
                                        ),
                                        retained.c.scope == scope,
                                    )
                                    .order_by(
                                        retained.c.created_at.desc(), retained.c.read_id.desc()
                                    )
                                    .limit(1),
                                    ("selected_read",),
                                ),
                            ),
                            (SelectInto(selected_head, ("head",)),),
                        ),
                    ),
                ),
                If(
                    head.is_(None),
                    (
                        Assign("freshness", literal("Unknown")),
                        Return(func.jsonb_build_object("payload", result)),
                    ),
                ),
                Assign(
                    "acquired",
                    func.ops.acquire_data_read_context(
                        func.jsonb_build_object("demand_id", head["demand_id"], "scope", scope).op(
                            "||"
                        )(func.jsonb_strip_nulls(func.jsonb_build_object("read_id", selected_read)))
                    ),
                ),
                Assign("selected_read", context["read_id"].astext),
                If(
                    last,
                    (
                        _refusal(
                            ~select(1)
                            .select_from(settled)
                            .where(
                                settled.c.project_id == p["project_id"].astext,
                                settled.c.name == p["selection_name"].astext,
                                settled.c.generation
                                == cast(head["generation"].astext, selections.c.generation.type),
                                settled.c.scope == scope,
                                settled.c.read_id == selected_read,
                            )
                            .exists(),
                            "read lacks exact settled coverage",
                            "22023",
                        ),
                        Perform(
                            func.ops.ddo_authorize_governed_coverage(
                                func.jsonb_build_object("read_id", selected_read)
                            )
                        ),
                        Assign("freshness", literal("Fresh")),
                    ),
                    (
                        Assign(
                            "observation",
                            func.ops.ddo_governed_settlement(
                                func.jsonb_build_object("read_id", selected_read)
                            ),
                        ),
                        Assign("observation", summary),
                        If(
                            observation["selection_generation"].is_distinct_from(head["generation"])
                            | observation["coverage_complete"].astext.is_distinct_from("true"),
                            (Assign("observation", _json("null")),),
                        ),
                        Assign(
                            "freshness",
                            func.coalesce(
                                func.nullif(observation["state"].astext, "pending"), "Pending"
                            ),
                        ),
                        If(
                            observation["state"].astext == "settled",
                            (
                                Assign("freshness", literal("Fresh")),
                                SelectInto(
                                    insert(settled)
                                    .values(
                                        project_id=p["project_id"].astext,
                                        name=p["selection_name"].astext,
                                        generation=cast(
                                            head["generation"].astext, selections.c.generation.type
                                        ),
                                        read_id=selected_read,
                                        scope=scope,
                                        created_at=_clock(),
                                        created_xid=_xid(),
                                    )
                                    .on_conflict_do_nothing()
                                    .returning(settled.c.read_id),
                                    ("recorded_read",),
                                ),
                            ),
                            (
                                If(
                                    observation["state"].astext == "unavailable",
                                    (Assign("freshness", literal("Unavailable")),),
                                    (
                                        If(
                                            and_(
                                                observation["uncovered_count"].astext == "0",
                                                cast(
                                                    observation["obligation_count"].astext,
                                                    selections.c.generation.type,
                                                )
                                                > 0,
                                                observation.is_not(None),
                                            ),
                                            (Assign("freshness", literal("Pending")),),
                                            (Assign("freshness", literal("Unknown")),),
                                        ),
                                    ),
                                ),
                            ),
                        ),
                    ),
                ),
                Return(func.jsonb_build_object("payload", result)),
            ),
            (
                Local("head", pg_type("jsonb")),
                Local("acquired", pg_type("jsonb")),
                Local("observation", pg_type("jsonb")),
                Local("freshness", pg_type("text")),
                Local("selected_read", pg_type("text")),
                Local("recorded_read", pg_type("text")),
            ),
        ),
        security_definer=True,
        search_path=("pg_catalog", "pg_temp"),
    )
    return ProgramDeclaration(
        routine,
        source="data-operations:forward",
        owner=role_name("publisher"),
        access=NativeProgramAccess(purposes=("read", "write", "evaluate")),
    )
