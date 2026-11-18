"""Compile domain purpose, support-scope locks and explicit trust epoch meaning."""

from typing import get_args, get_type_hints

from sqlalchemy import (
    Boolean,
    MetaData,
    Numeric,
    Text,
    and_,
    case,
    cast,
    column,
    func,
    literal,
    null,
    or_,
    select,
    tuple_,
    union,
)
from sqlalchemy.dialects.postgresql import JSONB, array, insert

from .binding_recursive_native import _check, _each, _elements, _json, _value
from .data_operation_projections import lock_support_scopes
from .native_definition_projection import NativeKindProjection
from .native_objects import native_sql_script
from .native_program import (
    Assign,
    Block,
    ForQuery,
    If,
    Local,
    Parameter,
    Return,
    SelectInto,
    Sql,
    column_type,
    core_variable,
    function,
    pg_type,
    sql_function,
)


def _object(key, value):
    return func.jsonb_build_object(key, value, type_=JSONB())


def _routine(
    name, parameters, steps, locals_=(), *, returns="jsonb", definer=False, volatility=None
):
    return (
        function(
            "ops",
            name,
            parameters=parameters,
            returns=pg_type(returns),
            body=Block(tuple(steps), tuple(locals_)),
            security_definer=definer,
            volatility=volatility,
            search_path=("pg_catalog", "pg_temp"),
        )
        + ";\n"
    )


def support_trust_native_sql(model):
    """Generate seven guards over captured physical and closed domain declarations."""
    trust = model.tables["ops.data_trust_scope"]
    requests = model.tables["ops.data_request"]
    reads = model.tables["ops.data_demand_read"]
    universe, project, source, scope_key = (
        _value(name) for name in ("universe", "project", "source", "scope_key")
    )
    snapshot = _value("snapshot", JSONB())
    principal = func.coalesce(
        func.nullif(func.current_setting("role"), "none"), func.session_user()
    )
    authorized = func.pg_has_role(principal, "corpus_sem_evaluator", "MEMBER", type_=Boolean())
    authorize = _routine(
        "ddo_authorize",
        (Parameter("universe", pg_type("text")),),
        (
            _check(
                and_(universe == "evaluator", ~authorized),
                "evaluator data requires evaluator purpose",
                "42501",
            ),
            _check(
                ~universe.in_(get_args(get_type_hints(NativeKindProjection)["universe"])),
                "unknown data universe",
            ),
        ),
        returns="void",
        definer=True,
        volatility="stable",
    )
    scope = _routine(
        "ddo_scope",
        (Parameter("project", pg_type("text")), Parameter("source", pg_type("text"))),
        (
            _check(
                or_(func.nullif(project, "").is_(None), source == ""),
                "trust scope requires real project and valid source context",
                "23514",
            ),
            Return(
                case(
                    (
                        source.is_(None),
                        literal("project:") + func.ops.ddo_digest(func.jsonb_build_array(project)),
                    ),
                    else_=literal("source:")
                    + func.ops.ddo_digest(func.jsonb_build_array(project, source)),
                )
            ),
        ),
        returns="text",
        volatility="immutable",
    )
    pairs = _each(snapshot, "epoch_pair")
    pair_key, pair_value = _value("pair_key"), _value("pair_value", JSONB())
    epoch, result = _value("epoch", Numeric()), _value("result", JSONB())
    meaning = _routine(
        "ddo_trust_snapshot_meaning",
        (Parameter("snapshot", pg_type("jsonb")),),
        (
            _check(
                func.jsonb_typeof(snapshot).is_distinct_from("object"),
                "trust snapshot requires an explicit epoch mapping",
            ),
            ForQuery(
                ("pair_key", "pair_value"),
                select(pairs.c.key, pairs.c.value),
                (
                    _check(
                        or_(
                            func.nullif(pair_key, "").is_(None),
                            func.jsonb_typeof(pair_value).is_distinct_from("number"),
                        ),
                        "trust snapshot requires nonnegative integer epochs",
                    ),
                    Assign("epoch", cast(pair_value.op("#>>")(array([], type_=Text())), Numeric())),
                    _check(
                        or_(epoch < 0, epoch != func.trunc(epoch)),
                        "trust snapshot requires nonnegative integer epochs",
                    ),
                    # Lazy scope creation does not change trust: absent and zero share
                    # one meaning, while the acquired snapshot still records exact zeros.
                    If(epoch != 0, (Assign("result", result.op("||")(_object(pair_key, epoch))),)),
                ),
            ),
            Return(result),
        ),
        (
            Local("pair_key", pg_type("text")),
            Local("pair_value", pg_type("jsonb")),
            Local("epoch", pg_type("numeric")),
            Local("result", pg_type("jsonb"), _json("{}")),
        ),
        volatility="immutable",
    )
    scopes = lock_support_scopes(model)

    def lock_steps(query):
        return (
            ForQuery(
                ("scope_key",),
                query,
                (
                    Sql(
                        insert(trust)
                        .values(scope=scope_key, project_id=project, epoch=0)
                        .on_conflict_do_nothing()
                    ),
                    SelectInto(
                        select(trust.c.epoch)
                        .where(trust.c.scope == scope_key)
                        .with_for_update(read=True),
                        ("e",),
                    ),
                    Assign(
                        "snapshot",
                        snapshot.op("||")(
                            _object(scope_key, core_variable("e", trust.c.epoch.type))
                        ),
                    ),
                ),
            ),
            Return(snapshot),
        )

    lock_locals = (
        Local("scope_key", pg_type("text")),
        Local("snapshot", pg_type("jsonb"), _json("{}")),
        Local("e", column_type(trust.c.epoch)),
    )
    locked = _routine(
        "ddo_lock_support",
        (
            Parameter("project", pg_type("text")),
            Parameter("source", pg_type("text")),
            Parameter("support", pg_type("jsonb")),
        ),
        lock_steps(scopes),
        lock_locals,
        definer=True,
    )
    ordinary = scopes.subquery("ordinary_scopes")
    request = _value("r")
    extras = tuple(
        getattr(func.ops, name)(request)
        .table_valued(column("scope", Text()))
        .render_derived(name=alias)
        for name, alias in (
            ("ddo_record_grade_completion_scopes", "grade_completion"),
            ("ddo_record_fit_completion_scopes", "fit_completion"),
            ("ddo_operation_event_completion_scopes", "event_completion"),
        )
    )
    completion_scopes = union(
        select(ordinary.c.scope), *(select(extra.c.scope) for extra in extras)
    ).order_by("scope")
    completion = _routine(
        "ddo_lock_completion_support",
        (
            Parameter("r", pg_type(str(requests.schema), requests.name)),
            Parameter("completion", pg_type("jsonb")),
        ),
        lock_steps(completion_scopes),
        (
            Local(
                "project",
                column_type(requests.c.project_id),
                core_variable("r", requests.c.project_id.type, "project_id"),
            ),
            Local(
                "source",
                column_type(requests.c.original_source),
                core_variable("r", requests.c.original_source.type, "original_source"),
            ),
            Local("support", pg_type("jsonb"), _value("completion", JSONB())["support"]),
            *lock_locals,
        ),
        definer=True,
    )
    freeze = _routine(
        "ddo_refuse_post_acquisition_graph_write",
        (),
        (
            _check(
                select(reads.c.id)
                .where(reads.c.owner_xid == cast(func.pg_current_xact_id(), Text()))
                .exists(),
                "support/frontier writes require a fresh transaction after demand read acquisition",
                "25001",
            ),
            Return(null()),
        ),
        returns="trigger",
        definer=True,
    )
    reference, row = (_value(name, JSONB()) for name in ("reference", "row_value"))
    references = _elements(
        func.coalesce(row["support_references"], _json("[]")), "support_reference"
    )
    item = references.c.value
    matches = (
        sql_function(
            "ops",
            "ddo_support_reference_matches",
            parameters=(
                Parameter("reference", pg_type("jsonb")),
                Parameter("row_value", pg_type("jsonb")),
            ),
            returns=pg_type("boolean"),
            body=select(
                select(item)
                .where(
                    or_(
                        and_(
                            func.coalesce(reference["kind"].astext, "computation") == "computation",
                            item["kind"].astext == "computation",
                            reference["derivation_id"].astext == item["derivation_id"].astext,
                            or_(
                                reference["admission_use_id"].astext.is_(None),
                                reference["admission_use_id"].astext
                                == item["admission_use_id"].astext,
                            ),
                        ),
                        and_(
                            reference["kind"].astext.in_(("original-source", "authored")),
                            reference["kind"].astext == item["kind"].astext,
                            tuple_(
                                reference["admission_id"].astext,
                                reference["source_reference"].astext,
                            )
                            == tuple_(item["admission_id"].astext, item["source_reference"].astext),
                        ),
                    )
                )
                .exists()
            ),
            volatility="immutable",
            strict=True,
            search_path=("pg_catalog", "pg_temp"),
        )
        + ";\n"
    )
    return "\n".join((authorize, scope, meaning, locked, completion, freeze, matches))


def support_scope_sql(model: MetaData) -> str:
    """Generate the shared SQL-language scope projection after its domain providers."""
    result = pg_type("record")
    result.setof = True
    return native_sql_script(
        (
            sql_function(
                "ops",
                "ddo_support_scopes",
                parameters=(
                    Parameter("project", pg_type("text")),
                    Parameter("source", pg_type("text")),
                    Parameter("support", pg_type("jsonb")),
                ),
                returns=result,
                table_columns=(("scope", pg_type("text")),),
                body=lock_support_scopes(model),
                volatility="stable",
                security_definer=True,
                search_path=("pg_catalog", "pg_temp"),
            ),
        )
    )


def trust_snapshot_changed(expected, observed):
    """Compare the explicit nonzero scope epochs of two acquisitions."""
    return func.ops.ddo_trust_snapshot_meaning(expected).is_distinct_from(
        func.ops.ddo_trust_snapshot_meaning(observed)
    )


def locked_support_changed(pinned, locked):
    """Require every positively observed lock epoch to match its pinned scope."""
    return ~func.ops.ddo_trust_snapshot_meaning(pinned, type_=JSONB()).contains(
        func.ops.ddo_trust_snapshot_meaning(locked)
    )
