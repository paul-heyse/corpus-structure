"""Generated admission of declared partition bodies and placement commitments."""

from dataclasses import dataclass

from pglast import ast, enums
from sqlalchemy import (
    BigInteger,
    Boolean,
    Column,
    MetaData,
    Numeric,
    Table,
    Text,
    case,
    cast,
    column,
    func,
    literal,
    or_,
    select,
    tuple_,
)
from sqlalchemy.dialects.postgresql import JSON, JSONB, REGCLASS, aggregate_order_by, array, insert
from sqlalchemy.schema import CreateTable

from corpus_structure.schema.integrity import role_name

from .native_program import (
    Assign,
    ForQuery,
    If,
    Local,
    Perform,
    Raise,
    Return,
    SelectInto,
    Sql,
    core_variable,
    pg_type,
)
from .population_transfer import POPULATION_UPLOAD_FIELDS, POPULATION_UPLOAD_SCRATCH

_UPLOAD_FENCE = "ddo_population_upload_fence"


def population_upload_requested(completion):
    outputs = (
        func.jsonb_array_elements(completion["outputs"])
        .table_valued(column("value", JSONB()))
        .render_derived(name="population_outputs")
    )
    packets = (
        func.jsonb_array_elements(outputs.c.value["product"]["partitions"])
        .table_valued(column("value", JSONB()))
        .render_derived(name="population_packets")
        .lateral()
    )
    return or_(
        func.to_regclass(literal("pg_temp." + _UPLOAD_FENCE)).is_not(None),
        select(1).select_from(outputs.join(packets, literal(True))).exists(),
    )


def population_upload_fence(payload, release_id):
    names = ("request_id", "generation", "task_id", "attempt", "holder")
    return func.jsonb_build_object(
        *(part for name in names for part in (name, payload[name])), "release_id", release_id
    )


@dataclass(frozen=True)
class PopulationScratchSpec:
    """The same projected temporary relation for runtime and static authoring."""

    name: str
    source: Table
    fields: tuple[str, ...]

    @property
    def qualified_name(self) -> str:
        return "pg_temp." + self.name

    def relation(self) -> ast.RangeVar:
        return ast.RangeVar(schemaname="pg_temp", relname=self.name, inh=True)

    def row_table(self, *, creation: bool = False) -> Table:
        return Table(
            self.name,
            MetaData(),
            *(
                Column(field, self.source.c[field].type, nullable=self.source.c[field].nullable)
                for field in self.fields
            ),
            schema=None if creation else "pg_temp",
            prefixes=("TEMPORARY",) if creation else (),
            postgresql_on_commit="DROP" if creation else None,
        )

    def create_statement(self) -> CreateTable:
        return CreateTable(self.row_table(creation=True))

    def owner_statement(self) -> ast.AlterTableStmt:
        return ast.AlterTableStmt(
            relation=self.relation(),
            objtype=enums.ObjectType.OBJECT_TABLE,
            cmds=(
                ast.AlterTableCmd(
                    subtype=enums.AlterTableType.AT_ChangeOwner,
                    newowner=ast.RoleSpec(
                        roletype=enums.RoleSpecType.ROLESPEC_CSTRING,
                        rolename=role_name("publisher"),
                    ),
                ),
            ),
        )


def population_scratch_specs(model: MetaData) -> tuple[PopulationScratchSpec, ...]:
    if "ops.data_retained_population_item" not in model.tables:
        return ()
    return (
        PopulationScratchSpec(
            POPULATION_UPLOAD_SCRATCH,
            model.tables["ops.data_retained_population_item"],
            POPULATION_UPLOAD_FIELDS,
        ),
        PopulationScratchSpec(
            _UPLOAD_FENCE, model.tables["ops.data_completion_intent"], ("payload",)
        ),
    )


def _authorize_upload_table(spec: PopulationScratchSpec):
    return Perform(
        func.ops.ddo_require_population_scratch(
            spec.name,
            cast(literal(spec.source.fullname), REGCLASS()),
            array(list(spec.fields), type_=Text()),
        )
    )


def population_upload_programs(model, output, routine):
    """Prepare publisher-owned scratch without taking a task or request lock across COPY."""
    from .pdf_staging_native import private_scratch_authorization_routine

    output.append(
        private_scratch_authorization_routine("ddo_require_population_scratch", projected=True)
    )
    upload_spec, fence_spec = population_scratch_specs(model)
    fence = fence_spec.row_table()
    request, task = tuple(model.tables[key] for key in ("ops.data_request", "ops.task"))
    parameter_names = ("request_id", "generation", "task_id", "attempt", "holder", "release_id")
    params = dict(
        zip(parameter_names, ("text", "bigint", "bigint", "bigint", "text", "text"), strict=True)
    )
    values = {
        name: core_variable("p_" + name, BigInteger() if kind == "bigint" else Text())
        for name, kind in params.items()
    }
    request_row = core_variable("request_row", request.c.id.type)
    binding = func.jsonb_build_object(*(part for item in values.items() for part in item))

    def prepare_table(spec: PopulationScratchSpec):
        return (
            If(
                func.to_regclass(literal(spec.qualified_name)).is_(None),
                (Sql(spec.create_statement()),),
            ),
            _authorize_upload_table(spec),
            Sql(
                ast.TruncateStmt(
                    relations=(spec.relation(),), behavior=enums.DropBehavior.DROP_RESTRICT
                )
            ),
        )

    current_attempt = (
        select(1)
        .select_from(request.join(task, task.c.id == request.c.live_task_id))
        .where(
            request.c.id == values["request_id"],
            request.c.release_id == values["release_id"],
            request.c.generation == values["generation"],
            task.c.data_request_id == request.c.id,
            task.c.data_generation == request.c.generation,
            task.c.id == values["task_id"],
            task.c.attempt == values["attempt"],
            task.c.claimed_by == values["holder"],
            task.c.status == "running",
            task.c.lease_until > func.clock_timestamp(),
        )
        .exists()
    )
    routine(
        output,
        "prepare_data_population_upload",
        tuple(("p_" + name, kind) for name, kind in params.items()),
        (
            SelectInto(
                select(request).where(request.c.id == values["request_id"]),
                ("request_row",),
                strict=True,
            ),
            Perform(func.ops.ddo_authorize_request(request_row)),
            If(~current_attempt, (Raise("stale data population upload fence", "23514"),)),
            *prepare_table(upload_spec),
            *prepare_table(fence_spec),
            Sql(insert(fence).values(payload=binding)),
            Sql(
                ast.GrantStmt(
                    is_grant=True,
                    targtype=enums.GrantTargetType.ACL_TARGET_OBJECT,
                    objtype=enums.ObjectType.OBJECT_TABLE,
                    objects=(upload_spec.relation(),),
                    privileges=(ast.AccessPriv(priv_name="insert"),),
                    grantees=(
                        ast.RoleSpec(
                            roletype=enums.RoleSpecType.ROLESPEC_CSTRING,
                            rolename=role_name("writer"),
                        ),
                    ),
                    behavior=enums.DropBehavior.DROP_RESTRICT,
                )
            ),
        ),
        (Local("request_row", request),),
        returns="void",
    )

    expected = core_variable("p_fence", JSONB())
    actual = core_variable("v_fence", JSONB())
    routine(
        output,
        "ddo_require_population_upload",
        (("p_fence", "jsonb"),),
        (
            _authorize_upload_table(upload_spec),
            _authorize_upload_table(fence_spec),
            SelectInto(select(fence.c.payload), ("v_fence",), strict=True),
            If(
                actual.is_distinct_from(expected),
                (Raise("population upload belongs to another attempt or release", "23514"),),
            ),
        ),
        (Local("v_fence", pg_type("jsonb")),),
        returns="void",
    )


def retained_population_programs(model, output, routine):
    """Admit exact item rows under a retained intent and promote by association."""
    from .data_operation_value_native import canonical_text_digest
    from .data_product_admission_native import product_identity

    request = model.tables["ops.data_request"]
    kind = model.tables["sem.data_kind_contract"]
    release_kind = model.tables["sem.data_kind_release"]
    parents = model.tables["ops.data_retained_population"]
    items = model.tables["ops.data_retained_population_item"]
    visible = model.tables["kb.data_product_population"]
    upload_spec, _ = population_scratch_specs(model)
    upload = upload_spec.row_table()
    upload_fields = upload_spec.fields
    intent = core_variable("p_intent", Text())
    completion = core_variable("p_completion", JSONB())
    product_key = core_variable("p_product", Text())
    output_role = core_variable("p_output_role", Text())
    output_position = core_variable("p_output_position", parents.c.output_position.type)
    partition_count = core_variable("p_partition_count", BigInteger())
    empty = cast(literal("[]"), JSONB())
    parent_key = ("intent_id", "output_role", "output_position", "collection", "partition_key")
    upload_key = parent_key[1:]

    def r(name):
        return core_variable("r", request.c[name].type, name)

    def obj(**fields):
        return func.jsonb_build_object(
            *(value for pair in fields.items() for value in pair), type_=JSONB()
        )

    def tagged(tag, value):
        return func.jsonb_build_array(tag, value)

    def rows(value, name):
        return (
            func.jsonb_array_elements(value)
            .table_valued(column("value", JSONB()), with_ordinality="ordinality")
            .render_derived(name=name)
        )

    def entries(value, name):
        return (
            func.jsonb_each(value)
            .table_valued(column("key", Text()), column("value", JSONB()))
            .render_derived(name=name)
        )

    def reject(condition, message):
        return If(condition, (Raise(message, "23514"),))

    def key_match(left, right, names):
        return tuple_(*(left.c[name] for name in names)) == tuple_(
            *(right.c[name] for name in names)
        )

    context = obj(
        project_id=r("project_id"),
        subject=r("subject"),
        subject_definition=func.ops.ddo_operation_subject(r("release_id"), r("operation_id")),
        original_source=r("original_source"),
        analyzed_scope=r("analyzed_scope"),
    )
    output_rows = rows(completion["outputs"], "output_row")
    supplied = output_rows.c.value["product"]
    kind_contract = supplied["kind_contract"].astext
    body = func.data.ddo_normalize(supplied["body"], type_=JSONB())
    candidates = (
        select(
            output_rows.c.value["role"].astext.label("output_role"),
            cast(output_rows.c.value["position"].astext, parents.c.output_position.type).label(
                "output_position"
            ),
            product_identity(context, kind_contract, func.data.ddo_identity("body", body)).label(
                "product_id"
            ),
            body.label("body"),
            supplied["partitions"].label("packets"),
            kind.c.collections.label("specification"),
        )
        .select_from(
            output_rows.outerjoin(kind, kind.c.kind_contract == kind_contract).outerjoin(
                release_kind,
                (release_kind.c.kind_contract == kind_contract)
                & (release_kind.c.release_id == r("release_id")),
            )
        )
        .where(supplied.has_key("partitions"), release_kind.c.kind_contract.is_not(None))
        .cte("typed_outputs")
    )
    packets = rows(candidates.c.packets, "packet").lateral()
    packet = packets.c.value
    headers = (
        select(
            candidates.c.output_role,
            candidates.c.output_position,
            packet["collection"].astext.label("collection"),
            packet["partition_key"].astext.label("partition_key"),
            candidates.c.product_id,
            cast(packet["ordinal"].astext, parents.c.ordinal.type).label("ordinal"),
            packet["partition_digest"].astext.label("partition_digest"),
            cast(packet["item_count"].astext, parents.c.item_count.type).label("item_count"),
            packet["group_digests"].label("group_digests"),
            packet["placement"].label("placement"),
        )
        .select_from(candidates.join(packets, literal(True)))
        .cte("typed_headers")
    )
    declarations = entries(candidates.c.specification["declarations"], "declared").lateral()
    declared = (
        select(
            candidates.c.output_role,
            candidates.c.output_position,
            declarations.c.key.label("collection"),
            declarations.c.value.label("declaration"),
            candidates.c.specification["schemas"][declarations.c.key].label("schema"),
            func.data.ddo_json(
                func.data.ddo_field(candidates.c.body, declarations.c.key), type_=JSONB()
            ).label("header"),
        )
        .select_from(candidates.join(declarations, literal(True)))
        .where(declarations.c.value["unit"].astext == "partitioned")
        .cte("typed_collections")
    )
    collection_key = upload_key[:-1]
    declarations_match = key_match(declared, headers, collection_key)
    count_headers = select(func.count()).select_from(headers).scalar_subquery()
    received_headers = (
        select(func.coalesce(func.sum(func.jsonb_array_length(supplied["partitions"])), 0))
        .select_from(output_rows)
        .scalar_subquery()
    )
    invalid_headers = (
        select(1)
        .select_from(headers.outerjoin(declared, declarations_match))
        .where(
            or_(
                declared.c.collection.is_(None),
                func.nullif(headers.c.partition_key, "").is_(None),
                cast(headers.c.placement["start"].astext, BigInteger()) < 0,
                cast(headers.c.placement["end"].astext, BigInteger())
                < cast(headers.c.placement["start"].astext, BigInteger()),
            )
        )
        .exists()
    )
    incoming = (
        select(
            *upload.c,
            func.data.ddo_normalize(cast(upload.c.canonical_text, JSONB()), type_=JSONB()).label(
                "item"
            ),
            declared.c.declaration,
            declared.c.schema,
        )
        .select_from(upload.join(declared, key_match(upload, declared, collection_key)))
        .cte("typed_incoming")
        .prefix_with("MATERIALIZED", dialect="postgresql")
    )
    item = incoming.c.item
    address_paths = rows(incoming.c.declaration["address"], "address_path")
    address = (
        select(
            func.jsonb_agg(
                aggregate_order_by(
                    func.data.ddo_json(
                        func.ops.ddo_partition_field(
                            item, address_paths.c.value[()].astext, type_=JSONB()
                        )
                    ),
                    address_paths.c.ordinality,
                )
            )
        )
        .select_from(address_paths)
        .correlate(incoming)
        .scalar_subquery()
    )
    group = entries(incoming.c.declaration["field_groups"], "field_group")
    paths = rows(group.c.value, "field_path")
    path = paths.c.value[()].astext
    field = func.ops.ddo_partition_field(item, path, type_=JSONB())
    group_item = tagged(
        "mapping",
        (
            select(
                func.coalesce(
                    func.jsonb_agg(
                        aggregate_order_by(
                            func.jsonb_build_array(path, field), func.convert_to(path, "UTF8")
                        )
                    ),
                    empty,
                )
            )
            .select_from(paths)
            .where(field.is_not(None))
            .correlate(incoming, group)
            .scalar_subquery()
        ),
    )
    projection = (
        select(func.jsonb_object_agg(group.c.key, group_item))
        .select_from(group)
        .correlate(incoming)
        .scalar_subquery()
    )
    valid_item = (
        (
            func.convert_to(func.data.canonical_json(item), "UTF8")
            == func.convert_to(incoming.c.canonical_text, "UTF8")
        )
        & func.public.json_matches_schema(
            cast(incoming.c.schema["meaning_schema"], JSON()), cast(item, JSON())
        ).is_(True)
        & func.public.json_matches_schema(
            cast(incoming.c.schema["body_schema"], JSON()), cast(func.data.ddo_json(item), JSON())
        ).is_(True)
    )

    def primitive(name, tag, datatype):
        value = func.ops.ddo_partition_field(item, name, type_=JSONB())
        payload = value[1].astext
        if tag == "integer":
            number = case((value[0].astext == tag, cast(payload, Numeric())))
            return case((number.between(-(2**63), 2**63 - 1), cast(number, datatype)))
        return case((value[0].astext == tag, cast(payload, datatype)))

    stored = (
        insert(items)
        .from_select(
            (
                "intent_id",
                *upload_fields,
                "address_key",
                "record_type",
                "start",
                "end",
                "declared_projection",
            ),
            select(
                intent,
                *(incoming.c[name] for name in upload_fields),
                cast(address, Text()),
                primitive("record_type", "string", items.c.record_type.type),
                primitive("start", "integer", items.c.start.type),
                primitive("end", "integer", items.c.end.type),
                projection,
            ).where(valid_item),
        )
        .returning(items.c.item_ordinal)
        .cte("typed_stored")
    )
    n_items = core_variable("v_item_count", BigInteger())
    actual_count = select(func.count()).select_from(upload).scalar_subquery()
    item_inventory = (
        select(
            *(items.c[name] for name in upload_key),
            func.count().label("count"),
            func.max(items.c.item_ordinal).label("last"),
            (
                literal("partition:")
                + canonical_text_digest(
                    literal('["ddo","partition","1",["sequence",[')
                    + func.string_agg(
                        items.c.canonical_text,
                        aggregate_order_by(literal(","), items.c.item_ordinal),
                    )
                    + literal("]]]")
                )
            ).label("digest"),
        )
        .where(items.c.intent_id == intent)
        .group_by(*(items.c[name] for name in upload_key))
        .cte("typed_item_inventory")
    )
    group_rows = entries(items.c.declared_projection, "group_item").lateral()
    group_inventory = (
        select(
            *(items.c[name] for name in upload_key),
            group_rows.c.key.label("group_name"),
            func.data.ddo_identity(
                "partition-group",
                tagged(
                    "sequence",
                    func.jsonb_agg(aggregate_order_by(group_rows.c.value, items.c.item_ordinal)),
                ),
            ).label("digest"),
        )
        .select_from(items.join(group_rows, literal(True)))
        .where(items.c.intent_id == intent)
        .group_by(*(items.c[name] for name in upload_key), group_rows.c.key)
        .cte("typed_group_inventory")
    )
    expected_group = entries(declared.c.declaration["field_groups"], "expected_group").lateral()
    group_commitments = (
        select(
            func.jsonb_object_agg(
                expected_group.c.key,
                func.coalesce(
                    group_inventory.c.digest,
                    func.data.ddo_identity("partition-group", tagged("sequence", empty)),
                ),
            )
        )
        .select_from(
            expected_group.outerjoin(
                group_inventory,
                key_match(group_inventory, parents, upload_key)
                & (group_inventory.c.group_name == expected_group.c.key),
            )
        )
        .correlate(parents, declared)
        .scalar_subquery()
    )
    wrong_population = (
        select(1)
        .select_from(
            parents.join(declared, key_match(parents, declared, collection_key)).outerjoin(
                item_inventory, key_match(parents, item_inventory, upload_key)
            )
        )
        .where(
            parents.c.intent_id == intent,
            or_(
                func.coalesce(item_inventory.c.count, 0) != parents.c.item_count,
                func.coalesce(item_inventory.c.last, -1) != parents.c.item_count - 1,
                func.coalesce(
                    item_inventory.c.digest,
                    func.data.ddo_identity("partition", tagged("sequence", empty)),
                ).is_distinct_from(parents.c.partition_digest),
                group_commitments.is_distinct_from(parents.c.group_digests),
            ),
        )
        .exists()
    )
    partition_order = func.convert_to(parents.c.partition_key, "UTF8")
    placement = tagged(
        "sequence",
        func.jsonb_build_array(
            tagged("string", parents.c.partition_key),
            tagged("integer", cast(parents.c.ordinal, Text())),
            tagged("integer", parents.c.placement["start"].astext),
            tagged("integer", parents.c.placement["end"].astext),
        ),
    )
    root_pairs = func.jsonb_build_array(parents.c.partition_key, parents.c.partition_digest)

    def commit_ordered(value):
        return func.coalesce(
            func.jsonb_agg(aggregate_order_by(value, partition_order)).filter(
                parents.c.partition_key.is_not(None)
            ),
            empty,
        )

    header_inventory = (
        select(1)
        .select_from(
            declared.outerjoin(
                parents,
                key_match(parents, declared, collection_key) & (parents.c.intent_id == intent),
            )
        )
        .group_by(*(declared.c[name] for name in collection_key), declared.c.header)
        .having(
            or_(
                func.coalesce(func.max(parents.c.ordinal), -1)
                != func.count(parents.c.partition_key) - 1,
                declared.c.header.is_distinct_from(
                    obj(
                        root=func.data.ddo_identity(
                            "partition-root", func.data.ddo_json_meaning(commit_ordered(root_pairs))
                        ),
                        placement_root=func.data.ddo_identity(
                            "partition-placement", tagged("sequence", commit_ordered(placement))
                        ),
                        partition_count=func.count(parents.c.partition_key),
                        item_count=func.coalesce(func.sum(parents.c.item_count), 0),
                    )
                ),
            )
        )
        .exists()
    )
    routine(
        output,
        "ddo_retain_population_rows",
        (("r", "ops.data_request"), ("p_intent", "text"), ("p_completion", "jsonb")),
        (
            reject(
                count_headers != received_headers, "population output kind is outside its release"
            ),
            reject(invalid_headers, "invalid retained population header"),
            Sql(
                insert(parents).from_select(
                    ("intent_id", *headers.c.keys()), select(intent, *headers.c)
                )
            ),
            reject(
                select(1)
                .select_from(upload)
                .where(
                    ~select(1)
                    .select_from(parents)
                    .where(parents.c.intent_id == intent, key_match(upload, parents, upload_key))
                    .correlate(upload)
                    .exists()
                )
                .exists(),
                "population item has no declared parent",
            ),
            SelectInto(select(func.count()).select_from(stored), ("v_item_count",), strict=True),
            reject(
                n_items != actual_count,
                "population item is not canonical or violates its declared schema",
            ),
            reject(
                wrong_population, "retained population items differ from their declared commitment"
            ),
            reject(
                header_inventory,
                "retained population collection header differs from its partitions",
            ),
        ),
        (Local("v_item_count", pg_type("bigint")),),
        returns="void",
    )

    p_fresh = core_variable("p_fresh", Boolean())
    p_fence = core_variable("p_fence", JSONB())
    retained = select(items).where(items.c.intent_id == intent).subquery("retained_items")
    replay_content_differs = (
        select(1)
        .select_from(
            upload.join(
                retained, key_match(upload, retained, (*upload_key, "item_ordinal")), full=True
            )
        )
        .where(upload.c.canonical_text.is_distinct_from(retained.c.canonical_text))
        .exists()
    )
    replay_differs = or_(
        actual_count != select(func.count()).select_from(retained).scalar_subquery(),
        replay_content_differs,
    )
    routine(
        output,
        "ddo_consume_population_upload",
        (
            ("r", "ops.data_request"),
            ("p_intent", "text"),
            ("p_completion", "jsonb"),
            ("p_fence", "jsonb"),
            ("p_fresh", "boolean"),
        ),
        (
            Perform(func.ops.ddo_require_population_upload(p_fence)),
            If(
                p_fresh,
                (
                    Perform(
                        func.ops.ddo_retain_population_rows(
                            core_variable("r", Text()), intent, completion
                        )
                    ),
                ),
                (reject(replay_differs, "population upload replay differs from retained items"),),
            ),
            Sql(
                ast.DropStmt(
                    objects=tuple(
                        (ast.String(sval="pg_temp"), ast.String(sval=name))
                        for name in (POPULATION_UPLOAD_SCRATCH, _UPLOAD_FENCE)
                    ),
                    removeType=enums.ObjectType.OBJECT_TABLE,
                    behavior=enums.DropBehavior.DROP_RESTRICT,
                )
            ),
        ),
        returns="void",
    )

    same_output = (
        parents.c.intent_id == intent,
        parents.c.output_role == output_role,
        parents.c.output_position == output_position,
    )
    visible_key = ("product_id", "collection", "partition_key")
    associated = parents.alias("associated")
    comparable = ("ordinal", "partition_digest", "item_count", "group_digests", "placement")
    routine(
        output,
        "ddo_promote_population_rows",
        (
            ("p_intent", "text"),
            ("p_output_role", "text"),
            ("p_output_position", "bigint"),
            ("p_product", "text"),
            ("p_partition_count", "bigint"),
        ),
        (
            reject(
                select(func.count()).select_from(parents).where(*same_output).scalar_subquery()
                .is_distinct_from(partition_count),
                "retained population does not cover the complete product manifest",
            ),
            reject(
                select(1)
                .select_from(parents)
                .where(*same_output, parents.c.product_id.is_distinct_from(product_key))
                .exists(),
                "retained population product identity differs",
            ),
            Sql(
                insert(visible)
                .from_select(
                    (*visible_key, "intent_id", "output_role", "output_position"),
                    select(
                        *(
                            parents.c[name]
                            for name in (
                                *visible_key,
                                "intent_id",
                                "output_role",
                                "output_position",
                            )
                        )
                    ).where(*same_output),
                )
                .on_conflict_do_nothing(index_elements=[visible.c[name] for name in visible_key])
            ),
            reject(
                select(1)
                .select_from(parents)
                .where(
                    *same_output,
                    ~select(1)
                    .select_from(
                        visible.join(associated, key_match(associated, visible, parent_key))
                    )
                    .where(
                        key_match(parents, visible, visible_key),
                        *(
                            associated.c[name].is_not_distinct_from(parents.c[name])
                            for name in comparable
                        ),
                    )
                    .correlate(parents)
                    .exists(),
                )
                .exists(),
                "visible population differs from the retained commitment",
            ),
        ),
        returns="void",
    )


def partition_projection_programs(output, routine):
    """Append shared item path and empty collection checks."""
    path_value = core_variable("p_value", JSONB())
    path_text = core_variable("p_path", Text())
    path_segment = core_variable("path_segment", Text())
    segments = (
        func.unnest(func.string_to_array(path_text, "."))
        .table_valued(column("value", Text()), with_ordinality="ordinality")
        .render_derived(name="path_segments")
    )
    routine(
        output,
        "ddo_partition_field",
        (("p_value", "jsonb"), ("p_path", "text")),
        (
            ForQuery(
                ("path_segment",),
                select(segments.c.value).order_by(segments.c.ordinality),
                (
                    If(
                        path_value[0].astext.is_distinct_from("mapping"),
                        (Return(cast(literal(None), JSONB())),),
                    ),
                    Assign("p_value", func.data.ddo_field(path_value, path_segment, type_=JSONB())),
                ),
            ),
            Return(path_value),
        ),
        (Local("path_segment", pg_type("text")),),
        returns="jsonb",
    )

    specification = core_variable("p_specification", JSONB())
    body = core_variable("p_body", JSONB())
    empty = cast(literal("[]"), JSONB())
    empty_object = cast(literal("{}"), JSONB())
    empty_sequence = func.jsonb_build_array("sequence", empty)
    expected = func.jsonb_build_object(
        "root",
        func.data.ddo_identity("partition-root", empty_sequence),
        "placement_root",
        func.data.ddo_identity("partition-placement", empty_sequence),
        "partition_count",
        0,
        "item_count",
        0,
    )
    declarations = (
        func.jsonb_each(func.coalesce(specification["declarations"], empty_object))
        .table_valued(column("key", Text()), column("value", JSONB()))
        .render_derived(name="declared_empty_population")
    )
    routine(
        output,
        "ddo_require_empty_product_populations",
        (("p_specification", "jsonb"), ("p_body", "jsonb")),
        (
            If(
                select(1).select_from(declarations).where(
                    declarations.c.value["unit"].astext == "partitioned",
                    func.data.ddo_json(
                        func.data.ddo_field(body, declarations.c.key)
                    ).is_distinct_from(expected),
                ).exists(),
                (Raise("partition collection header requires retained population items", "23514"),),
            ),
        ),
        returns="void",
    )
