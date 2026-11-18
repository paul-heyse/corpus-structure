"""Logical PDF target identity over exact published and observation lineage."""

from pglast import ast
from sqlalchemy import (
    BigInteger,
    Boolean,
    MetaData,
    Text,
    and_,
    cast,
    column,
    func,
    literal,
    select,
)
from sqlalchemy.dialects.postgresql import BYTEA, JSONB, aggregate_order_by, array

from .native_program import (
    Assign,
    Continue,
    Exit,
    ForQuery,
    If,
    Local,
    Perform,
    Raise,
    Return,
    SelectInto,
    While,
    call,
    column_type,
    core_relation_row,
    core_variable,
    pg_type,
    variable,
)
from .pdf_record_digest_native import _json, _private_function


def logical_target_identity(model: MetaData) -> tuple[str, str]:
    products = model.tables["ops.pdf_product"]
    schema = products.schema
    assert schema is not None
    published = model.tables["ops.pdf_published_revision"]
    validation = model.tables["ops.pdf_build_validation"]
    bodies = model.tables["ops.pdf_product_body"]
    inputs = model.tables["ops.pdf_product_input"]
    identity_fields = ("task_id", "product_key", "content_digest")
    pin_fields = tuple(products.c[name] for name in identity_fields)
    params = tuple(zip(("p_task", "p_key", "p_digest"), map(column_type, pin_fields), strict=True))
    task, key, digest = (
        core_variable(name, field.type) for (name, _), field in zip(params, pin_fields, strict=True)
    )

    def field(local, table, name):
        return core_variable(local, table.c[name].type, name)

    def local_values(local, table, names):
        return tuple(field(local, table, name) for name in names)

    artifact = field("root_", products, "artifact_digest")
    pin_task, pin_key, pin_digest, pin_kind, pin_release, pin_artifact, pin_contract = local_values(
        "pin_",
        products,
        (*identity_fields, "kind", "release_id", "artifact_digest", "contract_digest"),
    )
    in_task, in_key, in_digest, in_index, role = local_values(
        "input_",
        inputs,
        ("input_task_id", "input_product_key", "input_content_digest", "input_index", "role"),
    )
    payload, recipe = local_values("body_", bodies, ("payload", "recipe_digest"))

    def text_vars(*names):
        return tuple(core_variable(name, Text()) for name in names)

    def json_vars(*names):
        return tuple(core_variable(name, JSONB()) for name in names)

    item, pending, next_, resolved, target, assembled, selected = json_vars(
        "item_",
        "pending_",
        "next_",
        "resolved_",
        "target_",
        "inputs_",
        "selected_",
    )
    key_, root_key = text_vars("key_", "root_key_")
    ready, progress = (core_variable(name, Boolean()) for name in ("ready_", "progress_"))
    state, frame = (core_variable(name, BYTEA()) for name in ("state_", "frame_"))

    def same(left, right):
        return and_(*(left.c[name] == right.c[name] for name in identity_fields))

    def canonical(*values):
        return func.data.canonical_json(func.jsonb_build_array(*values), type_=Text())

    def body_digest(value):
        return func.encode(func.sha256(value), "hex")

    def contract(release, subpath):
        return func.ops.pdf_contract_input(release, subpath, type_=BYTEA())

    def json_array(source):
        items = func.jsonb_array_elements(source).table_valued(column("value", JSONB()))
        return select(items.c.value)

    lineage = select(
        task.label("task_id"),
        key.label("product_key"),
        digest.label("content_digest"),
    ).cte("lineage", recursive=True)
    parent = products.alias("parent_product")
    lineage = lineage.union(
        select(
            inputs.c.input_task_id, inputs.c.input_product_key, inputs.c.input_content_digest
        ).select_from(
            inputs.join(
                lineage,
                and_(
                    inputs.c.task_id == lineage.c.task_id,
                    inputs.c.product_key == lineage.c.product_key,
                ),
            ).join(parent, same(parent, lineage) & (parent.c.kind == "recognition_observation"))
        )
    )
    acquired = select(
        func.jsonb_agg(
            aggregate_order_by(
                func.to_jsonb(products.table_valued()),
                products.c.task_id,
                products.c.product_key.collate("C"),
            )
        )
    ).select_from(lineage.join(products, same(products, lineage)))
    admitted = (
        select(core_relation_row(published))
        .select_from(
            published.join(
                validation,
                and_(
                    validation.c.build_id == published.c.build_id,
                    validation.c.frozen_digest == published.c.frozen_digest,
                    validation.c.logical_digest == published.c.logical_digest,
                    validation.c.native_callbacks,
                ),
            )
        )
        .where(
            published.c.task_id == pin_task,
            published.c.product_key == pin_key,
            published.c.logical_digest == pin_digest,
            published.c.kind == pin_kind,
            published.c.release_id == pin_release,
            published.c.source_digest == pin_artifact,
            validation.c.contract_digest == pin_contract,
            body_digest(
                contract(
                    published.c.release_id, "implementation/pdf/docling-validation.schema.json"
                )
            )
            == published.c.schema_digest,
        )
    )

    rev_kind, rev_source, rev_schema, rev_recipe, rev_digest = local_values(
        "revision_",
        published,
        ("kind", "source_digest", "schema_digest", "recipe_digest", "logical_digest"),
    )
    profile = "pdf-published-target-v1"

    def meaning(kind, original, schema, recipe, logical):
        return func.jsonb_build_object(
            "version",
            profile,
            "kind",
            kind,
            "source_digest",
            original,
            "schema_digest",
            schema,
            "recipe_digest",
            recipe,
            "logical_digest",
            logical,
            type_=JSONB(),
        )

    under_pin = (inputs.c.task_id == pin_task, inputs.c.product_key == pin_key)
    sealed = (
        select(core_relation_row(bodies))
        .select_from(bodies)
        .where(
            bodies.c.task_id == pin_task,
            bodies.c.product_key == pin_key,
            body_digest(bodies.c.payload) == pin_digest,
            body_digest(contract(pin_release, "schema/pdf_products")) == pin_contract,
        )
    )
    observation = (
        SelectInto(sealed, ("body_",), strict=True),
        Assign("inputs_", _json("[]")),
        Assign("ready_", literal(True)),
        ForQuery(
            ("input_",),
            select(core_relation_row(inputs))
            .select_from(inputs)
            .where(*under_pin)
            .order_by(inputs.c.input_index),
            (
                Assign("selected_", resolved[canonical(in_task, in_key, in_digest)]),
                If(selected.is_(None), (Assign("ready_", literal(False)), Exit())),
                If(
                    in_index != func.jsonb_array_length(assembled),
                    (Raise("logical PDF target input inventory is not contiguous", "23514"),),
                ),
                Assign(
                    "inputs_",
                    assembled.op("||")(
                        func.jsonb_build_array(
                            func.jsonb_build_object(
                                "ordinal",
                                in_index,
                                "role",
                                role,
                                "target_meaning",
                                selected,
                            )
                        )
                    ),
                ),
            ),
        ),
        If(~ready, (Assign("next_", next_.op("||")(func.jsonb_build_array(item))), Continue())),
        If(
            ~select(1)
            .select_from(inputs)
            .where(*under_pin, inputs.c.role == "structural")
            .exists(),
            (Raise("logical observation lacks authentic raw lineage", "23514"),),
        ),
        Assign("state_", func.ops.pdf_identity_fold_start("records")),
        Assign(
            "frame_",
            func.ops.pdf_identity_record_frame(
                pin_contract,
                "observation",
                "root",
                array(["profile", "source", "recipe", "meaning", "inputs"], type_=Text()),
                array(
                    [
                        func.ops.pdf_identity_text(profile),
                        func.ops.pdf_identity_text(pin_artifact),
                        func.ops.pdf_identity_text(recipe),
                        func.ops.pdf_identity_text(
                            func.data.canonical_json(
                                func.data.ddo_json_meaning(
                                    func.ops.pdf_observation_meaning(payload)
                                )
                            )
                        ),
                        func.ops.pdf_identity_text(func.data.canonical_json(assembled)),
                    ],
                ),
            ),
        ),
        Assign(
            "state_", func.ops.pdf_identity_fold_step(state, cast(literal(0), BigInteger()), frame)
        ),
        Assign(
            "target_",
            meaning(
                pin_kind,
                pin_artifact,
                pin_contract,
                recipe,
                func.encode(
                    func.ops.pdf_identity_fold_finish(
                        state,
                        cast(literal(1), BigInteger()),
                        cast(func.octet_length(frame), BigInteger()),
                    ),
                    "hex",
                ),
            ),
        ),
    )
    capture = (
        Assign(
            "pin_",
            call(
                "pg_catalog",
                "jsonb_populate_record",
                ast.TypeCast(arg=ast.A_Const(isnull=True), typeName=pg_type(schema, products.name)),
                variable("item_"),
            ),
        ),
        Assign("key_", canonical(pin_task, pin_key, pin_digest)),
        If(
            pin_artifact.is_distinct_from(artifact),
            (Raise("logical PDF target changes original source", "23514"),),
        ),
        Perform(contract(pin_release, "implementation/pdf/staging-model.yaml")),
        If(
            pin_kind.in_(("native", "integrated")),
            (
                SelectInto(admitted, ("revision_",), strict=True),
                Assign(
                    "target_", meaning(rev_kind, rev_source, rev_schema, rev_recipe, rev_digest)
                ),
            ),
            (
                If(
                    pin_kind == "recognition_observation",
                    observation,
                    (
                        Raise(
                            literal("unsupported logical PDF target kind ").op("||")(pin_kind),
                            "23514",
                        ),
                    ),
                ),
            ),
        ),
        Assign("resolved_", func.jsonb_set(resolved, array([key_]), target)),
        Assign("progress_", literal(True)),
    )
    return _private_function(
        "pdf_identity_published_target",
        params,
        "jsonb",
        (
            SelectInto(
                select(core_relation_row(products))
                .select_from(products)
                .where(
                    products.c.task_id == task,
                    products.c.product_key == key,
                    products.c.content_digest == digest,
                ),
                ("root_",),
                strict=True,
            ),
            Assign("root_key_", canonical(task, key, digest)),
            # Recursive UNION collapses shared predecessors at their exact pin.
            SelectInto(acquired, ("pending_",)),
            While(
                func.jsonb_array_length(pending) > 0,
                (
                    Assign("next_", _json("[]")),
                    Assign("progress_", literal(False)),
                    ForQuery(("item_",), json_array(pending), capture),
                    If(
                        ~progress,
                        (Raise("logical PDF target has missing or cyclic input custody", "23514"),),
                    ),
                    Assign("pending_", next_),
                ),
            ),
            Return(resolved[root_key]),
        ),
        (
            Local("root_", products),
            Local("pin_", products),
            Local("revision_", published),
            Local("body_", bodies),
            Local("input_", inputs),
            Local("item_", pg_type("jsonb")),
            Local("pending_", pg_type("jsonb")),
            Local("next_", pg_type("jsonb")),
            Local("resolved_", pg_type("jsonb"), _json("{}")),
            Local("target_", pg_type("jsonb")),
            Local("inputs_", pg_type("jsonb")),
            Local("selected_", pg_type("jsonb")),
            Local("key_", pg_type("text")),
            Local("root_key_", pg_type("text")),
            Local("ready_", pg_type("bool")),
            Local("progress_", pg_type("bool")),
            Local("state_", pg_type("bytea")),
            Local("frame_", pg_type("bytea")),
        ),
        strict=True,
    )
