"""Current exact original-source readiness from the native binding owner."""

from sqlalchemy import Text, and_, case, cast, func, literal, select
from sqlalchemy.dialects.postgresql import JSONB

from .data_operation_projections import binding_columns
from .native_program import NativeRoutine, Parameter, core_variable, pg_type


def original_obligation_readiness(model):
    """Cover only a scalar source scan with no other binding premises.

    Immutable original admissions are the durable origin receipts. The admitted
    binding reader owns eligibility, disclosure and grouping of equal products;
    a raw product row or a publication from another episode supplies none of it.
    """
    obligations = model.tables["ops.data_obligation"]
    demands = model.tables["ops.data_demand"]
    reads = model.tables["ops.data_demand_read"]
    definitions = model.tables["sem.data_operation_definition"]
    kinds = model.tables["sem.data_kind_contract"]
    obligation = core_variable("p_obligation", Text())
    read = core_variable("p_read", Text())
    role = definitions.c.input_roles[0]
    expression = definitions.c.binding_expression

    def json(value):
        return cast(literal(value), JSONB())

    other_fields = func.jsonb_strip_nulls(expression)
    for field in ("operator", "roles", "impact", "fields", "children", "operands"):
        other_fields = other_fields.op("-")(field)
    covered = and_(
        func.ops.ddo_demand_active(demands.c.id),
        ~reads.c.public_disclosure,
        func.jsonb_array_length(definitions.c.input_roles) == 1,
        role["minimum"].astext == "1",
        role["maximum"].astext == "1",
        role["presence"].astext == "required",
        role["collection"].astext == "scalar",
        role["support"]["origins"] == json('["original-source"]'),
        role["support"]["source_set"].astext.is_(None),
        *(
            func.coalesce(role["support"][field], json("[]")) == json("[]")
            for field in ("authorization", "closure", "identity_requirements")
        ),
        func.coalesce(role["alternatives"], json("[]")) == json("[]"),
        role["parameter"].astext.is_(None),
        role["selected"].astext.is_(None),
        role["subject_field"].astext.is_(None),
        func.coalesce(role["subject_target"].astext, "subject") == "subject",
        func.coalesce(role["required_rules"], json("[]")) == json("[]"),
        kinds.c.universe.in_(("ordinary", "source")),
        definitions.c.dependencies == json('{"required":[],"potential":[]}'),
        func.coalesce(demands.c.selection["discovery"], json("[]")) == json("[]"),
        func.coalesce(
            func.nullif(demands.c.selection["source_sets"], json("null")), json("{}")
        )
        == json("{}"),
        expression["operator"].astext.in_(("scan", "all")),
        func.coalesce(expression["roles"], json("[]")).in_(
            (json("[]"), func.jsonb_build_array(role["name"]))
        ),
        *(
            func.coalesce(expression[field], json("[]")) == json("[]")
            for field in ("fields", "children", "operands")
        ),
        other_fields == json("{}"),
    )
    rows = (
        func.ops.ddo_binding_rows(
            demands.c.id,
            definitions.c.operation_id,
            reads.c.trust_snapshot,
            reads.c.id,
            obligations.c.subject,
            func.coalesce(func.to_jsonb(obligations.c.original_source), json("null")),
            obligations.c.analyzed_scope,
            literal(False),
            cast(literal(None), JSONB()),
        )
        .table_valued(*binding_columns())
        .render_derived(name="admitted_original_rows")
    )
    state = (
        select(
            func.jsonb_build_object(
                "ready",
                func.count() == 1,
                "state",
                case(
                    (func.count() == 1, "ready"), (func.count() == 0, "missing"), else_="ambiguous"
                ),
                "input_role",
                role["name"],
                "identity",
                case(
                    (
                        func.count() == 1,
                        func.jsonb_agg(
                            func.jsonb_build_object(
                                "product_id",
                                rows.c.product,
                                "admission_ids",
                                rows.c.support_evidence["original_admissions"],
                            ),
                            type_=JSONB(),
                        )[0],
                    ),
                    else_=cast(literal(None), JSONB()),
                ),
            )
        )
        .select_from(rows)
        .correlate(demands, definitions, reads, obligations)
        .scalar_subquery()
    )
    return NativeRoutine(
        "ops",
        "ddo_original_obligation_readiness",
        parameters=(
            Parameter("p_obligation", pg_type("text")),
            Parameter("p_read", pg_type("text")),
        ),
        returns=pg_type("jsonb"),
        body=select(case((covered, state), else_=cast(literal(None), JSONB())))
        .select_from(
            obligations.join(demands, demands.c.id == obligations.c.demand_id)
            .join(reads, reads.c.demand_id == demands.c.id)
            .join(
                definitions,
                and_(
                    definitions.c.release_id == demands.c.release_id,
                    definitions.c.operation_id == obligations.c.operation_id,
                ),
            )
            .join(kinds, kinds.c.kind_contract == role["kind_contract"].astext)
        )
        .where(obligations.c.id == obligation, reads.c.id == read),
        security_definer=True,
        volatility="volatile",
        search_path=("pg_catalog", "pg_temp"),
    )
