"""Captured product/member realization and exact original-source admission."""

from dataclasses import dataclass

from sqlalchemy import (
    BigInteger,
    Boolean,
    MetaData,
    Text,
    and_,
    case,
    cast,
    column,
    func,
    literal,
    or_,
    select,
    true,
    tuple_,
    union_all,
)
from sqlalchemy.dialects.postgresql import JSON, JSONB, array, insert
from sqlalchemy.sql.elements import ColumnElement

from .native_objects import native_sql_script
from .native_program import (
    Assign,
    Block,
    ForQuery,
    GetRowCount,
    If,
    Local,
    NativeRoutine,
    Parameter,
    Perform,
    Raise,
    Return,
    SelectInto,
    Sql,
    Statement,
    core_relation_row,
    core_variable,
    pg_type,
)


@dataclass(frozen=True)
class _Family:
    name: str
    attribute: str
    fields: tuple[tuple[str, str], ...]
    required: tuple[str, ...]
    optional: tuple[str, ...] = ()
    variants: tuple[tuple[str, tuple[tuple[str, ...], tuple[str, ...]]], ...] = ()


def _member_families(model):
    import yaml

    protocol = yaml.safe_load(model.info["physical_sources"]["data-operation-native.yaml"])
    schemas = protocol["definitions"]
    projections = (
        (
            "coordinate",
            "coordinates",
            ((name, name) for name in ("original_source", "start", "end", "page")),
        ),
        ("role", "roles", ((name, name) for name in ("role", "position", "multiplicity"))),
        (
            "endpoint",
            "endpoints",
            (
                ("role", "role"),
                ("endpoint_product", "product_id"),
                ("endpoint_member", "member_id"),
            ),
        ),
        ("coverage", "coverage", ((name, name) for name in ("scope", "start", "end", "complete"))),
        (
            "choice",
            "choices",
            ((name, name) for name in ("choice_group", "alternative", "selected")),
        ),
    )
    members = schemas["product_member"]["properties"]
    families = []
    for name, attribute, fields in projections:
        reference = members[attribute]["items"]["$ref"]
        if not reference.startswith("#/definitions/"):
            raise ValueError("member family requires a captured local protocol definition")
        schema = schemas[reference.removeprefix("#/definitions/")]
        fields = tuple(fields)
        if name == "endpoint":
            required, optional = (), ()
            variants = {}
            for branch in schema["oneOf"]:
                scope = branch["properties"]["scope"]["const"]
                order = ("scope", *(logical for _, logical in fields))
                variants[scope] = (
                    tuple(field for field in order if field in branch["required"]),
                    tuple(
                        field for field in branch["properties"] if field not in branch["required"]
                    ),
                )
            if set(variants) != {"local", "external"}:
                raise ValueError(
                    "endpoint projection requires its local and external scope contracts"
                )
        else:
            required = tuple(schema["required"])
            optional = tuple(field for field in schema["properties"] if field not in required)
            variants = {}
            if {logical for _, logical in fields} != schema["properties"].keys():
                raise ValueError("member family fields differ from physical projection: " + name)
        families.append(
            _Family(name, attribute, fields, required, optional, tuple(variants.items()))
        )
    return tuple(families)


def _items(value, name, *, ordered=False):
    return (
        func.jsonb_array_elements(value)
        .table_valued(
            column("value", JSONB()), **({"with_ordinality": "ordinality"} if ordered else {})
        )
        .render_derived(name=name)
    )


def _object(**fields):
    return func.jsonb_build_object(
        *(part for key, value in fields.items() for part in (key, value)), type_=JSONB()
    )


def _field(value, name):
    return func.data.ddo_field(value, name, type_=JSONB())


def _json(value):
    return func.data.ddo_json(value, type_=JSONB())


def _reject(condition, message, state="P0001"):
    return If(condition, (Raise(message, state),))


def _fields(value, required, optional=()):
    return Perform(
        func.ops.ddo_fields(
            value, array(list(required)), *([array(list(optional))] if optional else [])
        )
    )


def product_admission_native_sql(model: MetaData) -> str:
    return (
        native_sql_script(program.render() for program in product_admission_native_programs(model))
        + "\n"
    )


def product_admission_native_programs(model: MetaData) -> tuple[NativeRoutine, ...]:
    """Retain product realization bodies for the shared typed program registry."""
    output = []
    families = _member_families(model)
    _install_product(model, output, families)
    _original_admission(model, output, families)
    return tuple(output)


def _routine(output, name, params, statements, locals_=(), *, returns="jsonb"):
    output.append(
        NativeRoutine(
            "ops",
            name,
            parameters=tuple(Parameter(key, pg_type(kind)) for key, kind in params),
            returns=pg_type(returns),
            body=Block(tuple(statements), tuple(locals_)),
            security_definer=True,
            search_path=("pg_catalog", "pg_temp"),
        )
    )


def _install_product(model, output, families):
    kind, releases, product, members = (
        model.tables[name]
        for name in (
            "sem.data_kind_contract",
            "sem.data_kind_release",
            "kb.data_product",
            "kb.data_product_member",
        )
    )
    context, packet_in, scopes = (
        core_variable(name, JSONB()) for name in ("context", "o", "subject_scopes")
    )
    key, digest = core_variable("key", Text()), core_variable("bd", Text())
    body, m, raw, family_value, packet, member_context, canonical_members, member_body = (
        core_variable(name, JSONB())
        for name in (
            "b",
            "m",
            "raw",
            "family_value",
            "packet",
            "member_context",
            "canonical_members",
            "member_body",
        )
    )
    ordinal, inserted = (
        core_variable("n", BigInteger()),
        core_variable("inserted_product", BigInteger()),
    )
    empty = cast(literal("[]"), JSONB())

    def k(field):
        return core_variable("k", kind.c[field].type, field)

    def mk(field):
        return core_variable("member_kind", kind.c[field].type, field)

    def previous(field):
        return core_variable("previous", product.c[field].type, field)

    def lookup(name, relation, *where):
        return SelectInto(
            select(core_relation_row(relation)).select_from(relation).where(*where),
            (name,),
            strict=True,
        )

    def schema_matches(schema, value):
        return func.public.json_matches_schema(cast(schema, JSON()), cast(value, JSON()))

    member_rows = _items(packet_in["members"], "entry", ordered=True)
    canonical_rows = _items(canonical_members[1], "canonical", ordered=True)
    release_kind = (
        select(1)
        .select_from(releases)
        .where(
            releases.c.release_id == context["release_id"].astext,
            releases.c.kind_contract == mk("kind_contract"),
        )
        .exists()
    )
    family_checks = or_(
        *(
            or_(
                and_(
                    mk("families").bool_op("?")(family.name),
                    func.coalesce(raw[family.attribute], empty).is_distinct_from(
                        func.coalesce(m[family.attribute], empty)
                    ),
                ),
                and_(
                    ~mk("families").bool_op("?")(family.name),
                    func.coalesce(m[family.attribute], empty) != empty,
                ),
            )
            for family in families
        )
    )
    context_fields = ("subject", "subject_definition", "original_source", "analyzed_scope")
    product_context = _object(
        project_id=context["project_id"].astext,
        **{
            field: context[field] if field == "analyzed_scope" else context[field].astext
            for field in context_fields
        },
    )
    meaning = func.jsonb_build_array(
        "mapping",
        func.jsonb_build_array(
            func.jsonb_build_array("body", func.jsonb_build_array("string", digest)),
            func.jsonb_build_array("kind", func.jsonb_build_array("string", k("kind_contract"))),
            func.jsonb_build_array(
                "subject", func.jsonb_build_array("string", context["subject"].astext)
            ),
            func.jsonb_build_array("subject_context", func.data.ddo_json_meaning(product_context)),
        ),
    )
    member_steps = (
        _fields(
            m,
            ("member_id", "kind_contract", "context", "body"),
            tuple(f.attribute for f in families),
        ),
        _fields(m["context"], context_fields),
        Assign("member_context", m["context"]),
        Assign("member_body", func.data.ddo_normalize(m["body"])),
        _reject(
            or_(
                packet[0].astext != "mapping",
                func.jsonb_array_length(packet[1]) != 4,
                _field(packet, "member_id").is_distinct_from(
                    func.jsonb_build_array("string", m["member_id"].astext)
                ),
                _field(packet, "kind_contract").is_distinct_from(
                    func.jsonb_build_array("string", m["kind_contract"].astext)
                ),
                _field(packet, "body").is_distinct_from(member_body),
                _json(_field(packet, "context")).is_distinct_from(member_context),
                func.nullif(member_context["subject"].astext, "").is_(None),
                func.nullif(member_context["subject_definition"].astext, "").is_(None),
                member_context["original_source"].astext.is_distinct_from(
                    context["original_source"].astext
                ),
            ),
            "member context/body differs from canonical container packet",
        ),
        Perform(
            func.ops.ddo_require_subject_source(
                scopes,
                member_context["subject_definition"].astext,
                member_context["original_source"].astext,
            )
        ),
        lookup("member_kind", kind, kind.c.kind_contract == m["kind_contract"].astext),
        Perform(func.ops.ddo_authorize(mk("universe"))),
        Assign("raw", _json(member_body)),
        _reject(
            or_(
                ~k("member_contracts").bool_op("?")(mk("kind_contract")),
                ~release_kind,
                ~schema_matches(mk("meaning_schema"), member_body),
                ~schema_matches(mk("body_schema"), raw),
            ),
            "member kind/body differs from declared nominal container member contract",
        ),
        _reject(
            or_(
                func.nullif(m["member_id"].astext, "").is_(None),
                ~schema_matches(k("member_schema"), raw),
            ),
            "invalid member contract",
        ),
        _reject(family_checks, "member projection differs from semantic body"),
    )
    statements = [
        _fields(context, ("project_id", "release_id", *context_fields)),
        Perform(
            func.ops.ddo_require_subject_source(
                scopes, context["subject_definition"].astext, context["original_source"].astext
            )
        ),
        _fields(packet_in, ("kind_contract", "body", "members"), ("artifact_digest",)),
        lookup("k", kind, kind.c.kind_contract == packet_in["kind_contract"].astext),
        Perform(func.ops.ddo_authorize(k("universe"))),
        _reject(
            ~select(1)
            .select_from(releases)
            .where(
                releases.c.release_id == context["release_id"].astext,
                releases.c.kind_contract == k("kind_contract"),
            )
            .exists(),
            "output kind is outside release",
        ),
        _reject(
            packet_in["artifact_digest"].astext.is_not(None),
            "artifact publication requires an authenticated staged receipt profile",
        ),
        Assign("b", func.data.ddo_normalize(packet_in["body"])),
        Perform(func.ops.ddo_body_access(k("kind_contract"), body)),
        _reject(
            or_(
                ~schema_matches(k("meaning_schema"), body),
                ~schema_matches(k("body_schema"), _json(body)),
                func.jsonb_typeof(packet_in["members"]) != "array",
            ),
            "body violates kind contract",
        ),
        If(
            k("member_schema") == cast(literal('{"not":{}}'), JSONB()),
            (
                _reject(
                    packet_in["members"] != empty,
                    "noncontainer kind cannot publish projected members",
                ),
            ),
            (
                Assign("canonical_members", _field(body, "members")),
                _reject(
                    or_(
                        canonical_members[0].astext.is_distinct_from("sequence"),
                        func.jsonb_array_length(canonical_members[1]).is_distinct_from(
                            func.jsonb_array_length(packet_in["members"])
                        ),
                    ),
                    "body/member projection count disagreement",
                ),
            ),
        ),
        _reject(
            select(1)
            .select_from(member_rows)
            .group_by(member_rows.c.value["member_id"].astext)
            .having(func.count() != 1)
            .exists(),
            "duplicate member local identity",
        ),
        Assign("bd", func.data.ddo_identity("body", body)),
        Assign("key", func.data.ddo_identity("product", meaning)),
        Sql(
            insert(product)
            .values(
                id=key,
                kind_contract=k("kind_contract"),
                project_id=context["project_id"].astext,
                **{
                    field: context[field] if field == "analyzed_scope" else context[field].astext
                    for field in context_fields
                },
                canonical_body=body,
                body_digest=digest,
                artifact_digest=packet_in["artifact_digest"].astext,
            )
            .on_conflict_do_nothing()
        ),
        GetRowCount("inserted_product"),
        lookup("previous", product, product.c.id == key),
        _reject(
            or_(
                *(
                    previous(field).is_distinct_from(expected)
                    for field, expected in (
                        ("kind_contract", k("kind_contract")),
                        ("project_id", context["project_id"].astext),
                        ("subject", context["subject"].astext),
                        ("subject_definition", context["subject_definition"].astext),
                        ("original_source", context["original_source"].astext),
                        ("body_digest", digest),
                        ("canonical_body", body),
                        ("analyzed_scope", context["analyzed_scope"]),
                    )
                )
            ),
            "product identity/custody collision",
        ),
        ForQuery(
            ("m", "packet"),
            select(member_rows.c.value, canonical_rows.c.value)
            .select_from(
                member_rows.join(
                    canonical_rows, member_rows.c.ordinality == canonical_rows.c.ordinality
                )
            )
            .order_by(member_rows.c.ordinality),
            member_steps,
        ),
        Sql(
            insert(members)
            .from_select(
                ("product_id", "member_id", "kind_contract", *context_fields, "body"),
                select(
                    key,
                    member_rows.c.value["member_id"].astext,
                    member_rows.c.value["kind_contract"].astext,
                    *(
                        member_rows.c.value["context"][field]
                        if field == "analyzed_scope"
                        else member_rows.c.value["context"][field].astext
                        for field in context_fields
                    ),
                    func.data.ddo_normalize(member_rows.c.value["body"]),
                )
                .where(inserted == 1)
                .order_by(member_rows.c.ordinality),
            )
            .on_conflict_do_nothing()
        ),
    ]
    family_steps: list[Statement] = [
        lookup("member_kind", kind, kind.c.kind_contract == m["kind_contract"].astext)
    ]
    for family in families:
        values = _items(func.coalesce(m[family.attribute], empty), "family_entry", ordered=True)
        if family.name == "endpoint":
            endpoint_shapes = dict(family.variants)
            validation = (
                If(
                    family_value["scope"].astext == "local",
                    (_fields(family_value, *endpoint_shapes["local"]),),
                    (
                        If(
                            family_value["scope"].astext == "external",
                            (_fields(family_value, *endpoint_shapes["external"]),),
                            (Raise("endpoint requires explicit local/external scope", "P0001"),),
                        ),
                    ),
                ),
                _reject(
                    or_(
                        ~mk("families").bool_op("?")("endpoint"),
                        ~select(1)
                        .select_from(product)
                        .where(
                            product.c.id
                            == case(
                                (family_value["scope"].astext == "local", key),
                                else_=family_value["product_id"].astext,
                            ),
                            product.c.project_id == context["project_id"].astext,
                            product.c.original_source.is_not_distinct_from(
                                context["original_source"].astext
                            ),
                        )
                        .exists(),
                    ),
                    "endpoint custody/family mismatch",
                ),
            )
        else:
            condition = ~mk("families").bool_op("?")(family.name)
            if family.name == "coordinate":
                condition = or_(
                    context["original_source"].astext.is_(None),
                    family_value["original_source"].astext.is_distinct_from(
                        context["original_source"].astext
                    ),
                    condition,
                )
            validation = (
                _fields(family_value, family.required, family.optional),
                _reject(
                    condition,
                    "coordinate source/family mismatch"
                    if family.name == "coordinate"
                    else "undeclared " + family.name + " family",
                ),
            )
        family_steps.append(
            ForQuery(
                ("family_value", "n"), select(values.c.value, values.c.ordinality - 1), validation
            )
        )
    statements.append(ForQuery(("m",), select(member_rows.c.value), tuple(family_steps)))
    packets = select(member_rows.c.value.label("member")).cte("member_packets")
    expected_queries = [
        select(
            literal("member").label("family"),
            packets.c.member["member_id"].astext.label("member_id"),
            literal(-1, BigInteger()).label("ordinal"),
            func.jsonb_build_array(
                packets.c.member["kind_contract"].astext,
                *(
                    packets.c.member["context"][field]
                    if field == "analyzed_scope"
                    else packets.c.member["context"][field].astext
                    for field in context_fields
                ),
                func.data.ddo_normalize(packets.c.member["body"]),
            ).label("value"),
        )
    ]
    actual_queries = [
        select(
            literal("member").label("family"),
            members.c.member_id,
            literal(-1, BigInteger()).label("ordinal"),
            func.jsonb_build_array(
                members.c.kind_contract,
                *(members.c[field] for field in context_fields),
                members.c.body,
            ).label("value"),
        ).where(members.c.product_id == key)
    ]

    def projected_values(family, relation, value):
        result: list[ColumnElement] = []
        for physical_field, logical_field in family.fields:
            if family.name == "endpoint" and physical_field == "endpoint_product":
                result.append(
                    case((value["scope"].astext == "local", key), else_=value["product_id"].astext)
                )
            else:
                result.append(cast(value[logical_field].astext, relation.c[physical_field].type))
        return result

    for family in families:
        relation = model.tables["kb.data_member_" + family.name]
        family_rows = _items(
            func.coalesce(member_rows.c.value[family.attribute], empty), "item", ordered=True
        ).lateral()
        projection = projected_values(family, relation, family_rows.c.value)
        statements.append(
            Sql(
                insert(relation)
                .from_select(
                    (
                        "product_id",
                        "member_id",
                        "ordinal",
                        *(physical for physical, _ in family.fields),
                    ),
                    select(
                        key,
                        member_rows.c.value["member_id"].astext,
                        family_rows.c.ordinality - 1,
                        *projection,
                    )
                    .select_from(member_rows.join(family_rows, true()))
                    .where(inserted == 1)
                    .order_by(member_rows.c.value["member_id"].astext, family_rows.c.ordinality),
                )
                .on_conflict_do_nothing()
            )
        )
        expected_rows = _items(
            func.coalesce(packets.c.member[family.attribute], empty), "expected_item", ordered=True
        ).lateral()
        expected_queries.append(
            select(
                literal(family.name),
                packets.c.member["member_id"].astext,
                expected_rows.c.ordinality - 1,
                func.jsonb_build_array(*projected_values(family, relation, expected_rows.c.value)),
            ).select_from(packets.join(expected_rows, true()))
        )
        actual_queries.append(
            select(
                literal(family.name),
                relation.c.member_id,
                relation.c.ordinal,
                func.jsonb_build_array(*(relation.c[field] for field, _ in family.fields)),
            ).where(relation.c.product_id == key)
        )
    expected, actual = (
        union_all(*expected_queries).cte("expected"),
        union_all(*actual_queries).cte("actual"),
    )
    mismatch = (
        select(func.coalesce(expected.c.ordinal, actual.c.ordinal))
        .select_from(
            expected.join(
                actual,
                and_(
                    expected.c.family == actual.c.family,
                    expected.c.member_id == actual.c.member_id,
                    expected.c.ordinal == actual.c.ordinal,
                ),
                full=True,
            )
        )
        .where(expected.c.value.is_distinct_from(actual.c.value))
        .order_by(
            func.coalesce(expected.c.member_id, actual.c.member_id),
            func.coalesce(expected.c.ordinal, actual.c.ordinal),
            func.coalesce(expected.c.family, actual.c.family),
        )
        .limit(1)
    )
    statements += [
        SelectInto(mismatch, ("n",)),
        _reject(
            core_variable("found", Boolean()),
            literal("member projection identity collision at ordinal ") + cast(ordinal, Text()),
            "23514",
        ),
        Return(key),
    ]
    _routine(
        output,
        "ddo_install_product_context",
        (("context", "jsonb"), ("o", "jsonb"), ("subject_scopes", "jsonb")),
        statements,
        (
            Local("k", kind),
            Local("key", pg_type("text")),
            Local("b", pg_type("jsonb")),
            Local("bd", pg_type("text")),
            Local("m", pg_type("jsonb")),
            Local("raw", pg_type("jsonb")),
            Local("family_value", pg_type("jsonb")),
            Local("n", pg_type("bigint")),
            Local("previous", product),
            Local("packet", pg_type("jsonb")),
            Local("member_context", pg_type("jsonb")),
            Local("canonical_members", pg_type("jsonb")),
            Local("member_body", pg_type("jsonb")),
            Local("member_kind", kind),
            Local("inserted_product", pg_type("bigint")),
        ),
        returns="text",
    )


def _original_admission(model, output, families):
    demands, kinds, releases, admissions = (
        model.tables[name]
        for name in (
            "ops.data_demand",
            "sem.data_kind_contract",
            "sem.data_kind_release",
            "ops.original_source_admission",
        )
    )
    p, frozen, fact, snapshot, scopes = (
        core_variable(name, JSONB())
        for name in ("p", "frozen", "fact", "snapshot", "subject_scopes")
    )
    kind, product, identity, key, kind_name, kind_universe = (
        core_variable(name, Text())
        for name in ("kind", "product", "identity", "key", "kind_name", "kind_universe")
    )
    rooted = core_variable("rooted", Boolean())
    empty, empty_object = cast(literal("[]"), JSONB()), cast(literal("{}"), JSONB())
    reference = p["reference"]

    def demand(field):
        return core_variable("d", demands.c[field].type, field)

    def admitted(field=None):
        return core_variable(
            "admitted", JSONB() if field is None else admissions.c[field].type, field
        )

    def lookup(name, relation, *where):
        return SelectInto(
            select(core_relation_row(relation)).select_from(relation).where(*where),
            (name,),
            strict=True,
        )

    scope_fields = ("subject", "subject_definition", "original_source", "analyzed_scope")
    authored_fact = _object(
        **{
            field: reference[field] if field == "analyzed_scope" else reference[field].astext
            for field in scope_fields
        },
        meaning_body=func.data.ddo_normalize(reference["meaning_body"]),
        evidence=_object(
            standing="authored",
            author_assertion=reference["author"].astext,
            selection_id=reference["selection_id"].astext,
            submitted_by=func.coalesce(
                func.nullif(func.current_setting("role"), "none"), func.session_user()
            ),
        ),
    )
    roots = _items(demand("root"), "root")
    packets = _items(
        case(
            (
                fact["meaning_body"][0].astext == "mapping",
                func.coalesce(_field(fact["meaning_body"], "members")[1], empty),
            ),
            else_=empty,
        ),
        "packet",
    )
    field_names = (
        func.unnest(array([family.attribute for family in families]))
        .table_valued(column("field", Text()))
        .render_derived(name="family_field")
    )
    body = _field(packets.c.value, "body")
    field_projection = (
        select(
            func.coalesce(
                func.jsonb_object_agg(
                    field_names.c.field, _json(_field(body, field_names.c.field))
                ),
                empty_object,
            )
        )
        .select_from(field_names)
        .where(_field(body, field_names.c.field).is_not(None))
        .correlate(packets)
        .scalar_subquery()
    )
    member_value = _object(
        member_id=_json(_field(packets.c.value, "member_id")),
        kind_contract=_json(_field(packets.c.value, "kind_contract")),
        context=_json(_field(packets.c.value, "context")),
        body=body,
    ).op("||")(field_projection)
    member_projection = (
        select(func.coalesce(func.jsonb_agg(member_value), empty))
        .select_from(packets)
        .scalar_subquery()
    )
    product_context = _object(
        project_id=demand("project_id"),
        release_id=demand("release_id"),
        **{
            field: fact[field] if field == "analyzed_scope" else fact[field].astext
            for field in scope_fields
        },
    )
    _routine(
        output,
        "ddo_admit_original_source",
        (("p_payload", "jsonb"),),
        (
            _fields(p, ("demand_id", "selection_name", "reference", "selectors")),
            lookup("d", demands, demands.c.id == p["demand_id"].astext),
            Assign("frozen", demand("selection")["original_sources"][p["selection_name"].astext]),
            _reject(
                or_(
                    frozen.is_(None),
                    frozen.is_distinct_from(p.op("-")("demand_id").op("-")("selection_name")),
                    reference["project_id"].astext.is_distinct_from(demand("project_id")),
                ),
                "original source selection differs from immutable demand",
            ),
            If(
                reference["kind"].astext == "authored-fact",
                (
                    _reject(
                        p["selectors"].is_distinct_from(
                            func.jsonb_build_array(_object(scope="authored-fact"))
                        ),
                        "authored input requires its explicit immutable selection scope",
                    ),
                    SelectInto(
                        select(kinds.c.kind, kinds.c.universe)
                        .select_from(
                            kinds.join(releases, releases.c.kind_contract == kinds.c.kind_contract)
                        )
                        .where(
                            releases.c.release_id == demand("release_id"),
                            kinds.c.kind_contract == reference["kind_contract"].astext,
                            kinds.c.universe.in_(("ordinary", "evaluator")),
                        ),
                        ("kind_name", "kind_universe"),
                        strict=True,
                    ),
                    Perform(func.ops.ddo_authorize(kind_universe)),
                    Assign("fact", authored_fact),
                ),
                (
                    If(
                        reference["kind"].astext == "original-document",
                        (
                            _reject(
                                p["selectors"].is_distinct_from(
                                    func.jsonb_build_array(_object(scope="whole-document"))
                                ),
                                "original document scope differs from immutable whole document",
                            ),
                            Assign("fact", func.ops.ddo_original_document_view(reference)),
                            Assign(
                                "kind_name",
                                literal(
                                    "https://corpus-structure.dev/semantic/data-operation-source/DdoOriginalDocument"
                                ),
                            ),
                        ),
                        (Raise("unknown original source admission reference", "P0001"),),
                    ),
                ),
            ),
            Assign("subject_scopes", func.ops.ddo_release_subject_scopes(demand("release_id"))),
            Perform(
                func.ops.ddo_require_subject_source(
                    scopes, fact["subject_definition"].astext, fact["original_source"].astext
                )
            ),
            Assign(
                "rooted",
                select(1)
                .select_from(roots)
                .where(
                    tuple_(
                        roots.c.value["subject"].astext, roots.c.value["original_source"].astext
                    ).is_not_distinct_from(
                        tuple_(fact["subject"].astext, fact["original_source"].astext)
                    ),
                    roots.c.value["analyzed_scope"] == fact["analyzed_scope"],
                )
                .exists(),
            ),
            _reject(~rooted, "authenticated source context is outside frozen roots"),
            Assign(
                "snapshot",
                func.ops.ddo_lock_support(
                    demand("project_id"), fact["original_source"].astext, empty
                ),
            ),
            Perform(func.ops.ddo_require_active_demand(demand("id"))),
            SelectInto(
                select(releases.c.kind_contract)
                .select_from(
                    releases.join(kinds, kinds.c.kind_contract == releases.c.kind_contract)
                )
                .where(releases.c.release_id == demand("release_id"), kinds.c.kind == kind_name),
                ("kind",),
                strict=True,
            ),
            Assign(
                "product",
                func.ops.ddo_install_product_context(
                    product_context,
                    _object(
                        kind_contract=kind, body=fact["meaning_body"], members=member_projection
                    ),
                    scopes,
                ),
            ),
            Assign("identity", func.ops.ddo_digest(reference)),
            Assign(
                "key",
                literal("original-admission:")
                + func.ops.ddo_digest(
                    func.jsonb_build_array(
                        demand("id"), p["selection_name"].astext, identity, p["selectors"], product
                    )
                ),
            ),
            Sql(
                insert(admissions)
                .values(
                    id=key,
                    demand_id=demand("id"),
                    project_id=demand("project_id"),
                    release_id=demand("release_id"),
                    selection_name=p["selection_name"].astext,
                    source_reference=identity,
                    reference=reference,
                    selectors=p["selectors"],
                    product_id=product,
                    subject=fact["subject"].astext,
                    original_source=fact["original_source"].astext,
                    analyzed_scope=fact["analyzed_scope"],
                    trust_snapshot=snapshot,
                    evidence=fact["evidence"],
                    created_at=func.clock_timestamp(),
                    created_xid=cast(func.pg_current_xact_id(), Text()),
                )
                .on_conflict_do_nothing()
            ),
            lookup(
                "admitted",
                admissions,
                admissions.c.demand_id == demand("id"),
                admissions.c.selection_name == p["selection_name"].astext,
            ),
            _reject(admitted("id") != key, "immutable original source admission changed"),
            _reject(
                ~func.ops.ddo_original_admission_valid(admitted()),
                "original source admission is revoked",
            ),
            Return(
                _object(
                    payload=_object(
                        admission_id=admitted("id"),
                        selection_name=admitted("selection_name"),
                        product_id=product,
                        kind_contract=kind,
                        subject=admitted("subject"),
                        subject_definition=fact["subject_definition"].astext,
                        original_source=admitted("original_source"),
                        analyzed_scope=admitted("analyzed_scope"),
                        source_reference=identity,
                        trust_snapshot=snapshot,
                        evidence=admitted("evidence"),
                    )
                )
            ),
        ),
        (
            Local("p", pg_type("jsonb"), core_variable("p_payload", JSONB())),
            Local("d", demands),
            *(Local(name, pg_type("jsonb")) for name in ("frozen", "fact")),
            *(Local(name, pg_type("text")) for name in ("kind", "product", "identity")),
            Local("snapshot", pg_type("jsonb")),
            *(Local(name, pg_type("text")) for name in ("kind_name", "kind_universe", "key")),
            Local("admitted", admissions),
            Local("rooted", pg_type("bool")),
            Local("subject_scopes", pg_type("jsonb")),
        ),
    )
    payload = core_variable("p_payload", JSONB())
    for name, discriminator, message in (
        (
            "admit_authored_data",
            "authored-fact",
            "authored admission requires its exact declared fact reference",
        ),
        (
            "admit_original_document_asset",
            "original-document",
            "original document reference discriminator differs",
        ),
    ):
        _routine(
            output,
            name,
            (("p_payload", "jsonb"),),
            (
                _reject(
                    payload["reference"]["kind"].astext.is_distinct_from(discriminator), message
                ),
                Return(func.ops.ddo_admit_original_source(payload)),
            ),
        )
