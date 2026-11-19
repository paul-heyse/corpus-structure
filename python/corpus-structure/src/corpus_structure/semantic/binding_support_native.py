"""Compile exact manifest support selection and derivation ledger positions."""

from sqlalchemy import Integer, Text, and_, case, cast, column, func, literal, or_, select
from sqlalchemy.dialects.postgresql import JSONB, aggregate_order_by

from .binding_recursive_native import _binding_declarations, _render_binding_programs
from .native_program import (
    Block,
    If,
    Local,
    NativeRoutine,
    Parameter,
    Raise,
    Return,
    ReturnQuery,
    SelectInto,
    core_variable,
    pg_type,
)
from .native_program_registry import ProgramDeclaration


def _elements(value, name):
    return (
        func.jsonb_array_elements(value)
        .table_valued(column("value", JSONB()))
        .render_derived(name=name)
    )


def _binding_support_native_routines(model):
    def value(name, type_=None):
        return core_variable(name, JSONB() if type_ is None else type_)

    empty = cast(literal("[]"), JSONB())
    binding, input_record, selected, canonical, matched, episodes = (
        value(name)
        for name in ("binding", "input_record", "selected", "canonical", "matched", "episodes")
    )
    items = _elements(selected, "selected_input")
    item = items.c.value
    unique = select(item).distinct().subquery("unique_values")
    unique_value = unique.c.value
    common = dict(strict=True, search_path=("pg_catalog", "pg_temp"))
    out = [
        NativeRoutine(
            "ops",
            "ddo_input_support_selection",
            parameters=(Parameter("input_record", pg_type("jsonb")),),
            returns=pg_type("jsonb"),
            volatility="immutable",
            body=Block(
                (
                    If(
                        or_(
                            func.jsonb_typeof(selected).is_distinct_from("array"),
                            select(item)
                            .where(
                                or_(
                                    func.jsonb_typeof(item).is_distinct_from("string"),
                                    item.op("#>>")(cast(literal("{}"), _text_array())) == "",
                                )
                            )
                            .exists(),
                        ),
                        (
                            Raise(
                                "input support requires an explicit canonical episode set", "23514"
                            ),
                        ),
                    ),
                    SelectInto(
                        select(
                            func.coalesce(
                                func.jsonb_agg(
                                    aggregate_order_by(
                                        unique_value,
                                        unique_value.op("#>>")(
                                            cast(literal("{}"), _text_array())
                                        ).collate("C"),
                                    )
                                ),
                                empty,
                            )
                        ),
                        ("canonical",),
                    ),
                    If(
                        selected.is_distinct_from(canonical),
                        (Raise("input support episode set is duplicated or unordered", "23514"),),
                    ),
                    Return(selected),
                ),
                (
                    Local("selected", pg_type("jsonb"), input_record["support_derivation_ids"]),
                    Local("canonical", pg_type("jsonb")),
                ),
            ),
            **common,
        )
    ]
    out.append(
        NativeRoutine(
            "ops",
            "ddo_single_input_support_episode",
            parameters=(Parameter("input_record", pg_type("jsonb")),),
            returns=pg_type("text"),
            volatility="immutable",
            body=Block(
                (
                    If(
                        func.jsonb_array_length(selected) != 1,
                        (Raise("input requires exactly one selected producing episode", "23514"),),
                    ),
                    Return(selected[0].astext),
                ),
                (
                    Local(
                        "selected",
                        pg_type("jsonb"),
                        func.ops.ddo_input_support_selection(input_record),
                    ),
                ),
            ),
            **common,
        )
    )
    outputs = model.tables["ops.data_derivation_output"]
    admissions = model.tables["ops.original_source_admission"]
    actual = _elements(binding["inputs"], "manifest_input")
    supports = _elements(binding["support"], "selected_support")
    support = supports.c.value
    supported_episode = (
        select(outputs.c.derivation_id)
        .where(
            outputs.c.derivation_id == support["derivation_id"].astext,
            outputs.c.product_id == input_record["product_id"].astext,
            or_(
                outputs.c.member_id.is_(None),
                outputs.c.member_id.is_not_distinct_from(input_record["member_id"].astext),
            ),
        )
        .exists()
    )
    supported_original = (
        select(admissions.c.id)
        .where(
            admissions.c.id == support["admission_id"].astext,
            admissions.c.product_id == input_record["product_id"].astext,
            admissions.c.source_reference == support["source_reference"].astext,
        )
        .exists()
    )
    known = _elements(matched, "known_support")
    episode_rows = (
        select(known.c.value["derivation_id"].astext.label("episode"))
        .where(func.coalesce(known.c.value["kind"].astext, "computation") == "computation")
        .distinct()
        .subquery("known")
    )
    returns = pg_type("jsonb")
    returns.setof = True
    out.append(
        NativeRoutine(
            "ops",
            "ddo_input_support_refs",
            parameters=(
                Parameter("binding", pg_type("jsonb")),
                Parameter("input_record", pg_type("jsonb")),
            ),
            returns=returns,
            volatility="stable",
            security_definer=True,
            body=Block(
                (
                    If(
                        ~select(actual.c.value).where(actual.c.value == input_record).exists(),
                        (Raise("support selection is not an exact manifest input", "23514"),),
                    ),
                    SelectInto(
                        select(func.coalesce(func.jsonb_agg(support), empty)).where(
                            support["role"].astext == input_record["role"].astext,
                            support["position"].is_not_distinct_from(input_record["position"]),
                            or_(
                                and_(
                                    func.coalesce(support["kind"].astext, "computation")
                                    == "computation",
                                    selected.bool_op("?")(support["derivation_id"].astext),
                                    supported_episode,
                                ),
                                and_(
                                    support["kind"].astext.in_(("original-source", "authored")),
                                    selected == empty,
                                    input_record["member_id"].astext.is_(None),
                                    supported_original,
                                ),
                            ),
                        ),
                        ("matched",),
                    ),
                    SelectInto(
                        select(
                            func.coalesce(
                                func.jsonb_agg(
                                    aggregate_order_by(
                                        episode_rows.c.episode, episode_rows.c.episode.collate("C")
                                    )
                                ),
                                empty,
                            )
                        ),
                        ("episodes",),
                    ),
                    If(
                        episodes.is_distinct_from(selected),
                        (
                            Raise(
                                "selected input episode set lacks exact authentic output support",
                                "23514",
                            ),
                        ),
                    ),
                    ReturnQuery(select(known.c.value)),
                ),
                (
                    Local(
                        "selected",
                        pg_type("jsonb"),
                        func.ops.ddo_input_support_selection(input_record),
                    ),
                    Local("matched", pg_type("jsonb")),
                    Local("episodes", pg_type("jsonb")),
                ),
            ),
            **common,
        )
    )
    reference = (
        func.ops.ddo_input_support_refs(binding, input_record)
        .table_valued(column("reference", JSONB()))
        .render_derived(name="selected_reference")
    )
    episode = (
        select(reference.c.reference["derivation_id"].astext.label("episode"))
        .where(func.coalesce(reference.c.reference["kind"].astext, "computation") == "computation")
        .distinct()
        .subquery("selected")
    )
    out.append(
        NativeRoutine(
            "ops",
            "ddo_input_support_episodes",
            parameters=(
                Parameter("binding", pg_type("jsonb")),
                Parameter("input_record", pg_type("jsonb")),
            ),
            returns=pg_type("jsonb"),
            body=select(
                func.coalesce(
                    func.jsonb_agg(
                        aggregate_order_by(episode.c.episode, episode.c.episode.collate("C"))
                    ),
                    empty,
                )
            ),
            volatility="stable",
            security_definer=True,
            **common,
        )
    )
    # Native TABLE output carries named fields so ledger positions remain separate
    # from semantic occurrence positions.

    inputs, roledefs = value("inputs"), value("roledefs")
    entries = (
        func.jsonb_array_elements(inputs)
        .table_valued(column("input", JSONB()), with_ordinality="ordinal")
        .render_derived(name="input_row")
    )
    definitions = _elements(roledefs, "role_definition").lateral("role_definition")
    input_, roledef = entries.c.input, definitions.c.value
    position = case(
        (roledef["collection"].astext == "sequence", cast(input_["position"].astext, Integer())),
        else_=cast(
            func.row_number().over(
                partition_by=input_["role"].astext,
                order_by=(
                    input_["product_id"].astext,
                    input_["member_id"].astext.nulls_first(),
                    input_["position"],
                    input_,
                    entries.c.ordinal,
                ),
            )
            - 1,
            Integer(),
        ),
    )
    result = pg_type("record")
    result.setof = True
    out.append(
        NativeRoutine(
            "ops",
            "ddo_derivation_input_positions",
            parameters=(
                Parameter("inputs", pg_type("jsonb")),
                Parameter("roledefs", pg_type("jsonb")),
            ),
            returns=result,
            table_columns=(
                ("input_record", pg_type("jsonb")),
                ("physical_position", pg_type("integer")),
            ),
            body=select(input_, position).select_from(
                entries.join(definitions, roledef["name"].astext == input_["role"].astext)
            ),
            volatility="immutable",
            **common,
        )
    )
    return tuple(out)


def _text_array():
    from sqlalchemy.dialects.postgresql import ARRAY

    return ARRAY(Text())


def binding_support_native_programs(model) -> tuple[ProgramDeclaration, ...]:
    return _binding_declarations(_binding_support_native_routines(model))


def binding_support_native_sql(model) -> str:
    """Render this provider's captured statements from typed declarations."""
    return _render_binding_programs(binding_support_native_programs(model), separator="\n")
