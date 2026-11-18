"""Compile semantic source addresses and acquired-source-set validation."""

from dataclasses import fields
from typing import get_type_hints

from sqlalchemy import (
    Boolean,
    Text,
    and_,
    case,
    cast,
    column,
    exists,
    func,
    literal,
    or_,
    select,
    true,
)
from sqlalchemy.dialects.postgresql import JSONB, array
from sqlalchemy.sql.elements import Grouping

from .data_operation_source_sets import FrozenSourceSet, SourceSetEntry
from .data_product_reference import DataProductMemberReference, DataProductReference
from .native_program import (
    Assign,
    Block,
    ForQuery,
    If,
    Local,
    Parameter,
    Perform,
    Raise,
    Return,
    SelectInto,
    core_variable,
    function,
    pg_type,
    sql_function,
)
from .selected_support import AllAdmissibleAcquisition, SelectedSupportAcquisition, SourceReadBasis


def source_set_native_sql() -> str:
    source_sets = core_variable("source_sets", JSONB())
    reference = core_variable("reference", JSONB())
    source_set = core_variable("source_set", JSONB())
    product, member, episode, producing_use = (core_variable(name, Text()) for name in ("product", "member", "episode", "producing_use"))
    emitting = core_variable("emitting", JSONB())
    project = core_variable("project", Text())
    subject_scopes = core_variable("subject_scopes", JSONB())
    named_key = core_variable("named", Text(), "key")
    named_value = core_variable("named", JSONB(), "value")
    entry, acquired, proof = (core_variable(name, JSONB()) for name in ("entry", "acquired", "proof"))
    mode = core_variable("mode_", Text())
    entries_by_address = core_variable("entries_by_address", JSONB())
    proof_addresses = core_variable("proof_addresses", JSONB())
    kind = func.pg_catalog.jsonb_typeof
    empty_object = cast(literal("{}", Text()), JSONB())
    empty_array = cast(literal("[]", Text()), JSONB())
    selected_kind = SelectedSupportAcquisition.model_fields["kind"].default
    all_kind = AllAdmissibleAcquisition.model_fields["kind"].default
    entry_fields = tuple(field.name for field in fields(SourceSetEntry))
    entry_types = get_type_hints(SourceSetEntry)
    required_strings = tuple(name for name in entry_fields if entry_types[name] is str)
    product_keys = tuple(name for name, type_ in get_type_hints(DataProductReference).items() if type_ is str)
    member_keys = tuple(name for name, type_ in get_type_hints(DataProductMemberReference).items() if type_ is str)

    def rows(value, name):
        return func.pg_catalog.jsonb_array_elements(value).table_valued(column("value", JSONB())).render_derived(name=name)

    def each(value, name):
        return func.pg_catalog.jsonb_each(value).table_valued(column("key", Text()), column("value", JSONB())).render_derived(name=name)

    def keys(value, name):
        return func.pg_catalog.jsonb_object_keys(value).table_valued(column("value", Text())).render_derived(name=name)

    def check(condition, message):
        return If(condition, (Raise(message, "P0001"),))

    def fields_check(value, names):
        return Perform(func.ops.ddo_fields(value, array(list(names), type_=Text())))

    def address(value, *, semantic=False):
        return cast(func.pg_catalog.jsonb_build_array(value["product_id" if semantic else "product"].astext, value["member_id" if semantic else "member"].astext), Text())

    def routine(name, params, statements, *, returns="void", locals_=(), strict=True):
        return function("ops", name, parameters=tuple(Parameter(name, pg_type(type_)) for name, type_ in params), returns=pg_type(returns),
                        body=Block(statements, locals_), volatility="immutable", strict=strict, search_path=("pg_catalog", "pg_temp"))

    ref_keys = keys(reference, "reference_key")
    reference_check = sql_function("ops", "ddo_semantic_source_reference", parameters=(Parameter("reference", pg_type("jsonb")),), returns=pg_type("bool"),
        body=select(and_(kind(reference) == "object", *(reference.has_key(name) for name in product_keys),
            ~exists(select(1).select_from(ref_keys).where(~ref_keys.c.value.in_((*product_keys, *member_keys)))),
            *(and_(kind(reference[name]) == "string", func.nullif(reference[name].astext, "").is_not(None)) for name in product_keys),
            *(or_(~reference.has_key(name), and_(kind(reference[name]) == "string", func.nullif(reference[name].astext, "").is_not(None))) for name in member_keys),
        )), volatility="immutable", strict=True, search_path=("pg_catalog", "pg_temp"))
    named_rows = each(source_sets, "source_set_item")
    meaning_query = select(func.coalesce(func.jsonb_object_agg(named_rows.c.key, named_rows.c.value["entries"]), empty_object)).scalar_subquery()
    meaning = routine("ddo_source_sets_meaning", (("source_sets", "jsonb"),), (Return(meaning_query),), returns="jsonb")

    acquired_rows = rows(source_set["acquisition"]["reads"], "acquired_read")
    proof_rows = rows(acquired_rows.c.value["proofs"], "acquired_proof")
    value = proof_rows.c.value
    proof_match = routine("ddo_source_set_proof_matches", (("source_set", "jsonb"), ("product", "text"), ("member", "text"), ("episode", "text"), ("producing_use", "text"), ("emitting", "jsonb")), (
        If(source_set["acquisition"]["kind"].astext == all_kind, (Return(literal(True)),)),
        If(source_set["acquisition"]["kind"].astext.is_distinct_from(selected_kind), (Return(literal(False)),)),
        Return(exists(select(1).select_from(acquired_rows.join(proof_rows, true())).where(
            value["product_id"].astext == product, value["member_id"].astext.is_not_distinct_from(member),
            value["support"]["derivation_id"].astext == episode, value["support"]["admission_use_id"].astext == producing_use, value["output"] == emitting,
        ))),
    ), returns="bool", strict=False)

    entries = rows(named_value["entries"], "entry_item")
    reads = rows(named_value["acquisition"]["reads"], "read_item")
    proofs = rows(acquired["proofs"], "proof_item")
    all_reads = rows(func.coalesce(named_value["acquisition"]["reads"], empty_array), "proof_read")
    all_proofs = rows(all_reads.c.value["proofs"], "proof_address")
    entry_names = func.unnest(array(list(required_strings), type_=Text())).table_valued(column("value", Text())).render_derived(name="entry_field")
    selected_validation = (
        fields_check(named_value["acquisition"], tuple(SelectedSupportAcquisition.model_fields)),
        check(kind(named_value["acquisition"]["reads"]).is_distinct_from("array"), "source acquisition requires exact grouped reads"),
        check(exists(select(1).select_from(reads).group_by(reads.c.value["selection"]["cut_id"].astext).having(func.count() != 1)), "duplicate source acquisition cut"),
        ForQuery(("acquired",), select(reads.c.value), (
            fields_check(acquired, tuple(SourceReadBasis.model_fields)),
            check(or_(acquired["selection"]["project_id"].astext.is_distinct_from(project), func.jsonb_array_length(acquired["proofs"]) == 0), "source acquisition changes project or has empty proof group"),
            check(exists(select(1).select_from(proofs).group_by(proofs.c.value).having(func.count() != 1)), "duplicate source acquisition proof"),
            ForQuery(("proof",), select(proofs.c.value), (
                check(or_(~entries_by_address.has_key(address(proof, semantic=True)), proof["support"]["kind"].astext.is_distinct_from("computation"), func.nullif(proof["support"]["admission_use_id"].astext, "").is_(None),
                    proof["output"]["member_id"].astext.is_not(None) & proof["output"]["member_id"].astext.is_distinct_from(proof["member_id"].astext)), "source proof differs from its semantic address/emitting member"),
            )),
        )),
    )
    validation = routine("ddo_validate_source_sets", (("source_sets", "jsonb"), ("project", "text"), ("subject_scopes", "jsonb")), (
        check(kind(source_sets) != "object", "frozen source sets must be a named object"),
        ForQuery(("named",), select(named_rows.c.key, named_rows.c.value), (
            fields_check(named_value, tuple(field.name for field in fields(FrozenSourceSet) if field.name != "name")),
            check(or_(named_key == "", kind(named_value["entries"]).is_distinct_from("array")), "source set requires an explicit name and current acquisition envelope"),
            SelectInto(select(func.coalesce(func.jsonb_object_agg(address(entries.c.value), entries.c.value), empty_object)), ("entries_by_address",)),
            Assign("mode_", named_value["acquisition"]["kind"].astext),
            check(or_(~mode.in_((selected_kind, all_kind)), mode.is_(None)), "unsupported source acquisition kind"),
            If(mode == all_kind, (fields_check(named_value["acquisition"], tuple(AllAdmissibleAcquisition.model_fields)),), selected_validation),
            SelectInto(select(func.coalesce(func.jsonb_object_agg(address(all_proofs.c.value, semantic=True), literal(True)), empty_object)).select_from(all_reads.join(all_proofs, true())), ("proof_addresses",)),
            check(exists(select(1).select_from(entries).group_by(entries.c.value["product"].astext, entries.c.value["member"].astext).having(func.count() != 1)), "duplicate qualified source-set product/member"),
            ForQuery(("entry",), select(entries.c.value), (
                fields_check(entry, entry_fields),
                check(or_(exists(select(1).select_from(entry_names).where(kind(entry.op("->", return_type=JSONB())(entry_names.c.value)).is_distinct_from("string"))), ~kind(entry["member"]).in_(("string", "null")),
                    entry["project_id"].astext.is_distinct_from(project), ~kind(entry["original_source"]).in_(("string", "null")),
                    *(func.nullif(entry[name].astext, "").is_(None) for name in ("subject", "subject_definition", "product")),
                    (entry["member"] != cast(literal("null"), JSONB())) & func.nullif(entry["member"].astext, "").is_(None)), "source-set entry differs from original qualified reference"),
                Perform(func.ops.ddo_require_subject_source(subject_scopes, entry["subject_definition"].astext, entry["original_source"].astext)),
                check(~func.ops.ddo_semantic_source_reference(entry["reference"], type_=Boolean()), "source sets require exact semantic product/member references"),
                check(or_(entry["reference"]["product_id"].astext.is_distinct_from(entry["product"].astext), entry["reference"]["member_id"].astext.is_distinct_from(entry["member"].astext),
                    entry["source_reference"].astext.is_distinct_from(Grouping(case((entry["reference"].has_key("member_id"), literal("member:").concat(func.ops.ddo_digest(entry["reference"]))), else_=entry["product"].astext)))), "source-set semantic reference differs from exact native product/member"),
                check((mode == selected_kind) & ~proof_addresses.has_key(address(entry)), "source entry lacks explicit producing proof"),
            )),
        )),
    ), locals_=(Local("named", pg_type("record")), Local("entry", pg_type("jsonb")), Local("acquired", pg_type("jsonb")), Local("proof", pg_type("jsonb")), Local("mode_", pg_type("text")), Local("entries_by_address", pg_type("jsonb")), Local("proof_addresses", pg_type("jsonb"))))
    return ";\n".join((reference_check, meaning, proof_match, validation)) + ";\n"
