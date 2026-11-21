"""Demand result acquisition and support revocation from the declared native model."""

from sqlalchemy import (
    BigInteger,
    Boolean,
    DateTime,
    Integer,
    MetaData,
    Text,
    and_,
    cast,
    func,
    literal,
    or_,
    select,
    update,
)
from sqlalchemy.dialects.postgresql import JSONB, insert
from sqlalchemy.types import NullType

from corpus_structure.schema.integrity import role_name

from .data_operation_native_identity import native_identity_field
from .data_operation_projections import (
    read_access_universes,
    read_page,
    read_scope_rows,
    read_selection,
)
from .data_read_boundary_native import read_presentation_check
from .demand_registration_native import (
    _authorize_selection,
    _clock,
    _identify,
    _items,
    _json,
    _owned_row,
    _refusal,
    _required,
    _xid,
)
from .native_objects import INTERNAL_PROGRAM, NativeProgramAccess, native_sql_script
from .native_program import (
    Assign,
    Block,
    ForQuery,
    If,
    Local,
    NativeRoutine,
    Parameter,
    PerformQuery,
    Raise,
    Return,
    SelectInto,
    Sql,
    core_relation_row,
    core_variable,
    pg_type,
)
from .native_program_registry import ProgramDeclaration
from .support_trust_native import trust_snapshot_changed


def _exact_row(table, *conditions):
    return select(core_relation_row(table)).select_from(table).where(*conditions)


def _endpoint(name, body, locals_, *, request=True):
    return NativeRoutine(
        "ops",
        name,
        parameters=(Parameter("p_payload", pg_type("jsonb")),) if request else (),
        returns=pg_type("jsonb"),
        body=Block(tuple(body), tuple(locals_)),
        security_definer=request,
        search_path=("pg_catalog", "pg_temp"),
        volatility=None if request else "volatile",
    )


def _read_demand_result(model, *, context_only=False):
    demand = model.tables["ops.data_demand"]
    read = model.tables["ops.data_demand_read"]
    read_scope = model.tables["ops.data_demand_read_scope"]
    trust = model.tables["ops.data_trust_scope"]
    payload = core_variable("p", JSONB())
    argument = core_variable("p_payload", JSONB())
    snapshot = core_variable("snapshot", JSONB())
    results = core_variable("results", JSONB())
    limit = core_variable("lim", Integer())
    view = core_variable("selected_view", Text())
    max_bytes = core_variable("selected_max_bytes", BigInteger())
    scope_key = core_variable("scope_key", trust.c.scope.type)
    epoch = core_variable("epoch", trust.c.epoch.type)
    scopes = core_variable("acquired_scopes", JSONB())
    demand_id, demand_selection, release, project = (
        _owned_row("d", demand, name) for name in ("id", "selection", "release_id", "project_id")
    )

    def pinned(name):
        return _owned_row("boundary", read, name)

    scope = func.coalesce(payload["scope"], _json("{}"), type_=JSONB())
    acquisition = payload.has_key("read_id")
    boundary = core_variable("boundary", NullType())
    pinned_demand = core_variable("d", NullType())
    scope_rows = read_scope_rows(model).subquery("scoped_read")
    discovered = _items(scopes, "acquired_scope")
    fact = discovered.c.value
    universe_rows = _items(pinned("access_universes"), "universe")
    boundary_columns = (
        "id",
        "demand_id",
        "read_snapshot",
        "frontier_at",
        "owner_xid",
        "trust_snapshot",
        "scope",
        "access_universes",
        "public_disclosure",
        "kernel_digest",
        "grade_census_eligible",
        "fit_census_eligible",
    )
    capture_row = {name: pinned(name) for name in boundary_columns}
    capture_row["trust_snapshot"] = snapshot
    return _endpoint(
        "acquire_data_read_context" if context_only else "read_demand_result",
        (
            SelectInto(
                _exact_row(demand, demand.c.id == payload["demand_id"].astext), ("d",), strict=True
            ),
            If(
                and_(~acquisition, scope == _json("{}")),
                (_authorize_selection(model, demand_selection, release),),
            ),
            _refusal(
                or_(
                    and_(
                        or_(
                            *(
                                payload.has_key(name)
                                for name in ("after", "read_snapshot", "frontier_at")
                            )
                        ),
                        ~acquisition,
                    ),
                ),
                "demand read selection/snapshot pins are incomplete or differ",
            ),
            Assign("selected_view", func.coalesce(payload["view"].astext, "frontier")),
            _refusal(view.not_in(("frontier", "products", "support")), "unknown demand read view"),
            Assign(
                "selected_max_bytes",
                func.coalesce(cast(payload["max_bytes"].astext, BigInteger()), 8 * 1024**2),
            ),
            _refusal(~max_bytes.between(1, 64 * 1024**2), "invalid product page byte bound"),
            Assign("lim", func.coalesce(cast(payload["limit"].astext, Integer()), 100)),
            Assign("after_key", func.coalesce(payload["after"].astext, "")),
            _refusal(~limit.between(1, 1000), "invalid demand read bound"),
            If(
                acquisition,
                (
                    SelectInto(
                        _exact_row(
                            read,
                            read.c.id == payload["read_id"].astext,
                            read.c.demand_id == demand_id,
                        ),
                        ("boundary",),
                        strict=True,
                    ),
                    _refusal(
                        pinned("scope").is_distinct_from(scope),
                        "read scope differs from its pinned acquisition",
                    ),
                    Assign("snapshot", func.ops.ddo_require_read_current(boundary, project)),
                    _refusal(
                        or_(
                            and_(
                                payload.has_key("read_snapshot"),
                                payload["read_snapshot"].astext.is_distinct_from(
                                    pinned("read_snapshot")
                                ),
                            ),
                            and_(
                                payload.has_key("frontier_at"),
                                cast(
                                    payload["frontier_at"].astext, DateTime(timezone=True)
                                ).is_distinct_from(pinned("frontier_at")),
                            ),
                        ),
                        "read acquisition pins differ",
                    ),
                ),
                (
                    Assign(
                        ("boundary", "id"),
                        literal("read:").op("||")(cast(func.gen_random_uuid(), Text())),
                    ),
                    Assign(("boundary", "demand_id"), demand_id),
                    Assign(("boundary", "read_snapshot"), cast(func.pg_current_snapshot(), Text())),
                    Assign(("boundary", "frontier_at"), _clock()),
                    Assign(("boundary", "owner_xid"), _xid()),
                    Assign(("boundary", "scope"), scope),
                    Assign(
                        ("boundary", "public_disclosure"),
                        ~func.pg_has_role(
                            func.coalesce(
                                func.nullif(func.current_setting("role"), "none"),
                                func.session_user(),
                            ),
                            role_name("evaluator"),
                            "MEMBER",
                            type_=Boolean(),
                        ),
                    ),
                    SelectInto(
                        select(
                            func.coalesce(
                                func.jsonb_agg(func.to_jsonb(scope_rows.table_valued())),
                                _json("[]"),
                            )
                        ).select_from(scope_rows),
                        ("acquired_scopes",),
                    ),
                    Assign(("boundary", "kernel_digest"), native_identity_field("read_closure")),
                    ForQuery(
                        ("scope_key",),
                        select(fact["scope"].astext).order_by(fact["scope"].astext),
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
                                ("epoch",),
                            ),
                            Assign(
                                "snapshot",
                                snapshot.op("||")(func.jsonb_build_object(scope_key, epoch)),
                            ),
                        ),
                    ),
                    Assign(("boundary", "trust_snapshot"), snapshot),
                    Assign(
                        ("boundary", "access_universes"),
                        read_access_universes(model).scalar_subquery(),
                    ),
                    Assign(
                        ("boundary", "grade_census_eligible"),
                        func.ops.ddo_read_census_eligible(pinned_demand, boundary, "grade"),
                    ),
                    Assign(
                        ("boundary", "fit_census_eligible"),
                        func.ops.ddo_read_census_eligible(pinned_demand, boundary, "fit"),
                    ),
                    SelectInto(
                        insert(read).values(capture_row).returning(core_relation_row(read)),
                        ("boundary",),
                    ),
                    Sql(
                        insert(read_scope).from_select(
                            ("read_id", "scope", "epoch", "ordinary", "domain"),
                            select(
                                pinned("id"),
                                fact["scope"].astext,
                                cast(
                                    snapshot[fact["scope"].astext].astext, read_scope.c.epoch.type
                                ),
                                cast(fact["ordinary"].astext, Boolean()),
                                cast(fact["domain"].astext, Boolean()),
                            ).select_from(discovered),
                        )
                    ),
                ),
            ),
            read_presentation_check(scope, pinned("public_disclosure")),
            _refusal(
                and_(
                    payload.has_key("selection"),
                    payload["selection"].is_distinct_from(read_selection()),
                ),
                "demand read selection/snapshot pins are incomplete or differ",
            ),
            _refusal(
                and_(
                    payload.has_key("trust_snapshot"),
                    trust_snapshot_changed(payload["trust_snapshot"], snapshot),
                ),
                "trust snapshot changed; reacquire demand read",
            ),
            PerformQuery(
                select(func.ops.ddo_authorize(universe_rows.c.value[()].astext)).select_from(
                    universe_rows
                )
            ),
            *(
                (
                    Return(
                        func.jsonb_build_object(
                            "demand_id",
                            demand_id,
                            "selection",
                            read_selection(),
                            "trust_snapshot",
                            snapshot,
                            "read_id",
                            pinned("id"),
                            "read_snapshot",
                            pinned("read_snapshot"),
                            "frontier_at",
                            pinned("frontier_at"),
                        )
                    ),
                )
                if context_only
                else (
                    SelectInto(read_page(model), ("results",)),
                    _refusal(
                        and_(
                            view.in_(("products", "support")),
                            func.octet_length(func.data.canonical_json(results)) > max_bytes,
                        ),
                        "complete native product page envelope exceeds max_bytes; reduce the page limit",
                    ),
                    Return(results),
                )
            ),
        ),
        (
            Local("p", pg_type("jsonb"), argument),
            Local("d", demand),
            Local("snapshot", pg_type("jsonb"), _json("{}")),
            Local("results", pg_type("jsonb")),
            Local("lim", pg_type("int4")),
            Local("after_key", pg_type("text")),
            Local("selected_view", pg_type("text")),
            Local("selected_max_bytes", pg_type("int8")),
            Local("boundary", read),
            Local("scope_key", pg_type("text")),
            Local("epoch", pg_type("int8")),
            Local("acquired_scopes", pg_type("jsonb")),
        ),
    )


def _revoke_support(model):
    requests = model.tables["ops.data_request"]
    derivations = model.tables["ops.data_derivation"]
    outputs = model.tables["ops.data_derivation_output"]
    admissions = model.tables["ops.original_source_admission"]
    products = model.tables["kb.data_product"]
    kinds = model.tables["sem.data_kind_contract"]
    trust = model.tables["ops.data_trust_scope"]
    revoked = model.tables["ops.data_revocation"]
    payload = core_variable("p_payload", JSONB())
    project, original, selector_kind, selector, reason = (
        payload[name].astext
        for name in ("project_id", "original_source", "selector_kind", "selector", "reason")
    )
    scope = core_variable("scope_key", trust.c.scope.type)
    epoch = core_variable("e", trust.c.epoch.type)
    key = core_variable("key", revoked.c.id.type)

    def context(row):
        return and_(
            row.c.project_id == project, row.c.original_source.is_not_distinct_from(original)
        )

    def matches(selectors):
        return or_(*(and_(selector_kind == name, column == selector) for name, column in selectors))

    episode_support = or_(
        matches(
            (
                ("derivation", derivations.c.id),
                ("recipe", derivations.c.recipe),
                ("runtime", derivations.c.runtime_id),
            )
        ),
        and_(
            selector_kind == "product",
            select(1)
            .select_from(outputs)
            .where(
                outputs.c.derivation_id == derivations.c.id,
                outputs.c.product_id == selector,
            )
            .correlate(derivations)
            .exists(),
        ),
    )
    admission_support = and_(
        context(admissions),
        matches(
            (
                ("original-admission", admissions.c.id),
                ("original-source", admissions.c.source_reference),
                ("product", admissions.c.product_id),
            )
        ),
    )
    selected = or_(
        select(1)
        .select_from(derivations.join(requests, requests.c.id == derivations.c.request_id))
        .where(context(requests), episode_support)
        .exists(),
        select(1).select_from(admissions).where(admission_support).exists(),
    )
    allowed_requests = (
        select(func.ops.ddo_authorize_request(requests.table_valued()))
        .select_from(requests)
        .where(
            context(requests),
            or_(
                matches((("recipe", requests.c.recipe), ("runtime", requests.c.runtime_id))),
                select(1)
                .select_from(derivations)
                .where(
                    derivations.c.request_id == requests.c.id,
                    episode_support,
                )
                .correlate(requests)
                .exists(),
            ),
        )
    )
    eligible_kind = (
        select(func.ops.ddo_authorize(kinds.c.universe))
        .select_from(
            admissions.join(products, products.c.id == admissions.c.product_id).join(
                kinds, kinds.c.kind_contract == products.c.kind_contract
            )
        )
        .where(admission_support)
    )
    return _endpoint(
        "revoke_data_support",
        (
            _required(
                payload, "project_id", "original_source", "selector_kind", "selector", "reason"
            ),
            _refusal(func.nullif(reason, "").is_(None), "revocation requires reason"),
            _refusal(~selected, "revocation selector outside project/source scope"),
            Assign("scope_key", func.ops.ddo_scope(project, original)),
            Sql(
                insert(trust)
                .values(scope=scope, project_id=project, epoch=0)
                .on_conflict_do_nothing()
            ),
            PerformQuery(
                select(1).select_from(trust).where(trust.c.scope == scope).with_for_update()
            ),
            PerformQuery(allowed_requests),
            PerformQuery(eligible_kind),
            SelectInto(
                update(trust)
                .where(trust.c.scope == scope)
                .values(epoch=trust.c.epoch + 1)
                .returning(trust.c.epoch),
                ("e",),
            ),
            Assign("key", _identify("revocation:", func.jsonb_build_array(scope, epoch, payload))),
            Sql(
                insert(revoked).values(
                    id=key,
                    scope=scope,
                    epoch=epoch,
                    selector_kind=selector_kind,
                    selector=selector,
                    reason=reason,
                    created_at=_clock(),
                )
            ),
            Return(
                func.jsonb_build_object(
                    "payload",
                    func.jsonb_build_object("revocation_id", key, "scope", scope, "epoch", epoch),
                )
            ),
        ),
        (
            Local("scope_key", pg_type("text")),
            Local("e", pg_type("int8")),
            Local("key", pg_type("text")),
        ),
    )


def demand_result_programs(model: MetaData) -> tuple[ProgramDeclaration, ...]:
    routines = (
        _revoke_support(model),
        _endpoint(
            "ddo_result_bytes_refusal",
            (
                Raise(
                    "native product page exceeds max_bytes; reduce the page limit or select a larger explicit bound",
                    "P0001",
                ),
            ),
            (),
            request=False,
        ),
        _read_demand_result(model),
        _read_demand_result(model, context_only=True),
    )
    return tuple(
        ProgramDeclaration(
            routine,
            source="data-operations:forward",
            owner=role_name("publisher"),
            access=NativeProgramAccess(purposes=("read", "write", "evaluate"))
            if routine.name == "acquire_data_read_context"
            else INTERNAL_PROGRAM,
        )
        for routine in routines
    )


def demand_result_sql(model: MetaData) -> str:
    """Render the captured result programs with an explicit kernel determinant."""
    return native_sql_script(
        declaration.routine.render() for declaration in demand_result_programs(model)
    )
