"""Model-bound protected observation publication and receipt projection.

The wire envelope remains JSON (not JSONB) until each owned collection is
visited, retaining duplicate-key detection and array order at the boundary.
"""

import json

from pglast import ast
from sqlalchemy import (
    BigInteger,
    Boolean,
    Integer,
    LargeBinary,
    Numeric,
    Text,
    and_,
    any_,
    case,
    cast,
    column,
    func,
    literal,
    literal_column,
    not_,
    or_,
    select,
    tuple_,
    union_all,
)
from sqlalchemy.dialects.postgresql import ARRAY, JSON, JSONB, aggregate_order_by, array, insert

from corpus_structure.model.compiled import field_kinds

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
    Sql,
    column_type,
    core_relation_row,
    core_variable,
    function,
    pg_type,
)
from .native_shapes import record_shape_steps
from .pdf_domain import pdf_call_bindings


def _object(*values):
    return func.jsonb_build_object(*values, type_=JSONB())


def _array(*values):
    return func.jsonb_build_array(*values, type_=JSONB())


def _json(value):
    return cast(literal(json.dumps(value, separators=(",", ":"))), JSONB())


def _rows(value, name, *, wire=False, ordinal=False):
    return (
        getattr(func, "json_array_elements" if wire else "jsonb_array_elements")(value)
        .table_valued(
            column("value", JSON() if wire else JSONB()),
            **({"with_ordinality": "n"} if ordinal else {}),
        )
        .render_derived()
        .alias(name)
    )


def _unnest(value, name, type_=None):
    return (
        func.unnest(value)
        .table_valued(column("value", LargeBinary() if type_ is None else type_))
        .render_derived()
        .alias(name)
    )


def _hash(value):
    return func.encode(func.sha256(value), "hex")


def _decode(value, *, wire=False):
    return cast(func.convert_from(value, "UTF8"), JSON() if wire else JSONB())


def _refuse(condition, message, state="23514"):
    return If(condition, (Raise(message, state),))


def _fields(value, names):
    return Perform(func.ops.ddo_fields(value, array(list(names), type_=Text())))


def _row(name, table):
    return {field.name: core_variable(name, field.type, field.name) for field in table.c}


def _exists(relation, *conditions):
    return select(1).select_from(relation).where(*conditions).exists()


def _select_row(table, name, *conditions, strict=False, lock=False):
    query = select(core_relation_row(table)).select_from(table).where(*conditions)
    return SelectInto(query.with_for_update() if lock else query, (name,), strict)


def _context(model):
    # pdf_task_context is a model-owned reader; fields match its declared tuple.
    request = model.tables["ops.data_request"]
    document = model.tables["kb.document"]
    artifact = model.tables["kb.source_artifact"]
    columns = {
        "request_id": request.c.id,
        "generation": request.c.generation,
        "release_id": request.c.release_id,
        "project_id": request.c.project_id,
        "document_id": document.c.id,
        "source_digest": artifact.c.artifact_digest,
    }
    return {name: core_variable("context", field.type, name) for name, field in columns.items()}


def observation_projection_declaration(context, model):
    """Project only exact retained observations from the supplied request basis."""
    from pydantic import TypeAdapter

    from .pdf_observations import PdfObservationPageReport

    tables = model.tables
    task, request, definition, product, body, artifact, runtime, revoked = (
        tables[name]
        for name in (
            "ops.task",
            "ops.data_request",
            "sem.data_operation_definition",
            "ops.pdf_product",
            "ops.pdf_product_body",
            "kb.source_artifact",
            "sem.runtime_binding",
            "ops.data_revocation",
        )
    )
    document, record_document, membership, native, owned = (
        tables[name]
        for name in (
            "kb.document",
            "ops.pdf_record_document",
            "kb.pdf_record_membership",
            "kb.pdf_record_native",
            "ops.pdf_product_artifact",
        )
    )
    p_receipt = core_variable("p_receipt", JSONB())
    p_task, p_attempt = (core_variable(name, BigInteger()) for name in ("p_task", "p_attempt"))
    p_holder = core_variable("p_holder", Text())
    ctx, req, prod, defin = (
        _context(model),
        _row("request", request),
        _row("product", product),
        _row("definition", definition),
    )
    values = {
        name: core_variable(name, JSONB())
        for name in (
            "profile",
            "selected",
            "capture",
            "page",
            "request_ref",
            "report",
            "result",
            "request_row",
            "payload",
            "origin",
            "requested",
            "available",
            "page_groups",
            "page_requests",
            "pages",
        )
    }
    (
        profile,
        selected,
        capture,
        page,
        ref,
        report,
        result,
        request_row,
        payload,
        origin,
        requested,
        available,
        groups,
        page_requests,
        pages,
    ) = values.values()
    ordinal = core_variable("ordinal", BigInteger())
    report_content, body_content, raw_payload = (
        core_variable(name, LargeBinary())
        for name in ("report_content", "body_content", "raw_payload")
    )
    previous_page, previous_outcome = (
        core_variable("previous_page", BigInteger()),
        core_variable("previous_outcome", Text()),
    )
    recovery_count = core_variable("recovery_count", Integer())
    bindings, recipes = (
        _rows(req["binding"]["inputs"], "bindings"),
        _rows(profile["recipes"], "recipes"),
    )
    numbers = _rows(requested, "numbers")
    page_rows, refs = (
        _rows(p_receipt["pages"], "page_rows", ordinal=True),
        _rows(page["observations"], "refs", ordinal=True),
    )
    readings = _rows(page_requests, "readings")
    report_request = report["requests"][cast(ordinal, Integer())]
    missing_artifacts = _unnest(
        array(
            [
                page["report_digest"].astext,
                report["result_digest"].astext,
                report_request["request_digest"].astext,
            ],
            type_=Text(),
        ),
        "required_artifacts",
        Text(),
    )
    schema = TypeAdapter(PdfObservationPageReport).json_schema(ref_template="#/definitions/{model}")
    if "$defs" in schema:
        schema["definitions"] = schema.pop("$defs")
    report_valid = func.public.json_matches_schema(
        cast(literal(json.dumps(schema)), JSON()), cast(report, JSON())
    )
    pin_conditions = (
        product.c.task_id == cast(ref["task_id"].astext, BigInteger()),
        product.c.product_key == ref["product_key"].astext,
        product.c.content_digest == ref["content_digest"].astext,
    )
    request_steps = (
        _fields(
            ref, ("ordinal", "task_id", "product_key", "content_digest", "publication_context")
        ),
        _select_row(product, "product", *pin_conditions, strict=True),
        Assign("origin", prod["publication_context"]),
        _refuse(
            or_(
                prod["kind"] != "recognition_observation",
                prod["task_id"] != p_task,
                prod["artifact_digest"].is_distinct_from(ctx["source_digest"]),
                origin.is_(None),
                origin.is_distinct_from(ref["publication_context"]),
                origin["version"].astext.is_distinct_from("pdf-observation-publication-1"),
                origin["request_id"].astext.is_distinct_from(ctx["request_id"]),
                cast(origin["generation"].astext, BigInteger()).is_distinct_from(ctx["generation"]),
                cast(origin["task_id"].astext, BigInteger()).is_distinct_from(p_task),
                origin["release_id"].astext.is_distinct_from(ctx["release_id"]),
                origin["source_digest"].astext.is_distinct_from(ctx["source_digest"]),
                not_(cast(origin["attempt"].astext, BigInteger()).between(1, p_attempt)),
                and_(
                    cast(origin["attempt"].astext, BigInteger()) == p_attempt,
                    or_(
                        origin["holder"].astext.is_distinct_from(p_holder),
                        origin["runtime_id"].astext.is_distinct_from(
                            p_receipt["runtime_id"].astext
                        ),
                    ),
                ),
                cast(ref["ordinal"].astext, BigInteger()).is_distinct_from(ordinal),
                cast(report_request["ordinal"].astext, BigInteger()).is_distinct_from(ordinal),
                not_(
                    _exists(
                        runtime,
                        runtime.c.release_id == origin["release_id"].astext,
                        runtime.c.runtime_id == origin["runtime_id"].astext,
                    )
                ),
                _exists(
                    revoked,
                    revoked.c.scope
                    == func.ops.ddo_scope(req["project_id"], req["original_source"]),
                    revoked.c.selector_kind == "runtime",
                    revoked.c.selector == origin["runtime_id"].astext,
                ),
            ),
            "observation publication/adoption loses original native attribution",
        ),
        SelectInto(
            select(body.c.payload).where(
                body.c.task_id == prod["task_id"], body.c.product_key == prod["product_key"]
            ),
            ("raw_payload",),
            True,
        ),
        Assign("payload", _decode(raw_payload)),
        SelectInto(
            select(artifact.c.content).where(
                artifact.c.artifact_digest == report_request["request_digest"].astext,
                _hash(artifact.c.content) == artifact.c.artifact_digest,
            ),
            ("body_content",),
            True,
        ),
        Assign("request_row", _decode(body_content)),
        _refuse(
            or_(
                _hash(raw_payload).is_distinct_from(prod["content_digest"]),
                payload["recipe_digest"].astext.is_distinct_from(page["recipe_digest"].astext),
                payload["observation"]["image"]["page_no"].astext.is_distinct_from(
                    page["page_no"].astext
                ),
                request_row["ordinal"].astext.is_distinct_from(ref["ordinal"].astext),
                request_row["submitted_digest"].astext.is_distinct_from(
                    payload["observation"]["image"]["artifact_digest"].astext
                ),
                request_row["outcome"].astext.is_distinct_from(
                    payload["observation"]["outcome"].astext
                ),
                cast(
                    case(
                        {"fullpage": "A", "detection": "B", "crop": "C"},
                        value=request_row["stage"].astext,
                    ),
                    Text(),
                ).is_distinct_from(payload["observation"]["pass_role"].astext),
                request_row.has_key("raw_response").is_distinct_from(
                    payload["observation"].has_key("raw_response_digest")
                ),
                and_(
                    request_row.has_key("raw_response"),
                    request_row["raw_digest"].astext.is_distinct_from(
                        payload["observation"]["raw_response_digest"].astext
                    ),
                ),
                _exists(
                    missing_artifacts,
                    not_(
                        _exists(
                            owned,
                            owned.c.task_id == prod["task_id"],
                            owned.c.product_key == prod["product_key"],
                            owned.c.artifact_digest == missing_artifacts.c.value,
                        )
                    ),
                ),
            ),
            "observation report/request bytes differ from native retained evidence",
        ),
        Assign(
            "page_requests",
            page_requests.concat(
                _array(
                    _object(
                        "ordinal",
                        ordinal,
                        "meaning_digest",
                        func.ops.ddo_digest(
                            func.data.ddo_json_meaning(
                                func.ops.pdf_observation_meaning(raw_payload)
                            )
                        ),
                        "pass_role",
                        payload["observation"]["pass_role"],
                        "outcome",
                        payload["observation"]["outcome"],
                    )
                )
            ),
        ),
    )
    page_steps = (
        _fields(
            page, ("page_no", "recipe_digest", "report_digest", "adapter_reused", "observations")
        ),
        _refuse(
            or_(
                func.jsonb_typeof(page["adapter_reused"]).is_distinct_from("boolean"),
                not_(requested.contains(_array(cast(page["page_no"].astext, BigInteger())))),
                not_(
                    _exists(
                        recipes, recipes.c.value["digest"].astext == page["recipe_digest"].astext
                    )
                ),
            ),
            "observation page/recipe differs from exact requested source",
        ),
        If(
            previous_page.is_distinct_from(cast(page["page_no"].astext, BigInteger())),
            (
                _refuse(
                    or_(
                        groups.contains(_array(cast(page["page_no"].astext, BigInteger()))),
                        page["recipe_digest"].astext.is_distinct_from(
                            profile["base_recipe_digest"].astext
                        ),
                    ),
                    "observation page ordering/base recipe differs",
                ),
                Assign(
                    "page_groups", groups.concat(_array(cast(page["page_no"].astext, BigInteger())))
                ),
                Assign("recovery_count", literal(0)),
            ),
            (
                Assign("recovery_count", recovery_count + 1),
                _refuse(
                    or_(
                        recovery_count != 1,
                        profile["recovery_policy"] == _json(None),
                        previous_outcome == "succeeded",
                        page["recipe_digest"].astext == profile["base_recipe_digest"].astext,
                    ),
                    "observation recovery differs from its finite admitted policy",
                ),
            ),
        ),
        SelectInto(
            select(artifact.c.content).where(
                artifact.c.artifact_digest == page["report_digest"].astext,
                _hash(artifact.c.content) == artifact.c.artifact_digest,
            ),
            ("report_content",),
            True,
        ),
        Assign("report", _decode(report_content)),
        _refuse(
            not_(func.coalesce(report_valid, False)),
            "observation report violates its finite manifest contract",
        ),
        _refuse(
            or_(
                report["page_no"].astext.is_distinct_from(page["page_no"].astext),
                report["recipe_digest"].astext.is_distinct_from(page["recipe_digest"].astext),
                func.jsonb_array_length(report["requests"]).is_distinct_from(
                    func.jsonb_array_length(page["observations"])
                ),
            ),
            "observation report differs from exact retained request inventory",
        ),
        SelectInto(
            select(artifact.c.content).where(
                artifact.c.artifact_digest == report["result_digest"].astext,
                _hash(artifact.c.content) == artifact.c.artifact_digest,
            ),
            ("body_content",),
            True,
        ),
        Assign("result", _decode(body_content)),
        _refuse(
            or_(
                result["outcome"].astext.is_(None),
                result["outcome"].astext.not_in(
                    ("succeeded", "partial", "failed", "unknown", "unsupported")
                ),
            ),
            "observation report lacks its actual reported page outcome",
        ),
        Assign("page_requests", _json([])),
        ForQuery(("request_ref", "ordinal"), select(refs.c.value, refs.c.n - 1), request_steps),
        _refuse(
            and_(
                result["outcome"].astext == "succeeded",
                or_(
                    func.jsonb_array_length(page_requests) < 2,
                    page_requests[0]["pass_role"].astext != "A",
                    page_requests[1]["pass_role"].astext != "B",
                    _exists(readings, readings.c.value["outcome"].astext != "succeeded"),
                ),
            ),
            "successful page report differs from actual retained pass outcomes",
        ),
        Assign(
            "pages",
            pages.concat(
                _array(
                    _object(
                        "page_no",
                        page["page_no"],
                        "recipe_digest",
                        page["recipe_digest"],
                        "outcome",
                        result["outcome"],
                        "observations",
                        page_requests,
                    )
                )
            ),
        ),
        Assign("previous_page", cast(page["page_no"].astext, BigInteger())),
        Assign("previous_outcome", result["outcome"].astext),
    )
    statements = (
        _fields(
            p_receipt,
            (
                "version",
                "request_id",
                "generation",
                "task_id",
                "attempt",
                "holder",
                "runtime_id",
                "source_digest",
                "recipe_digest",
                "pages",
            ),
        ),
        _select_row(task, "job", task.c.id == p_task, strict=True),
        SelectInto(
            select(literal_column("*")).select_from(func.ops.pdf_task_context(p_task)),
            ("context",),
            True,
        ),
        Assign("request", core_variable("p_request", JSONB())),
        _refuse(
            or_(
                *(
                    req[name].is_distinct_from(ctx[name])
                    for name in ("id", "generation", "release_id")
                    if name != "id"
                ),
                req["id"].is_distinct_from(ctx["request_id"]),
                req["project_id"].is_distinct_from(ctx["project_id"]),
                req["original_source"].is_distinct_from(
                    select(document.c.key)
                    .where(document.c.id == ctx["document_id"])
                    .scalar_subquery()
                ),
            ),
            "observation projection changes its actual task request basis",
        ),
        Perform(func.ops.ddo_authorize_request(core_variable("request", JSONB()))),
        _select_row(
            definition,
            "definition",
            definition.c.release_id == ctx["release_id"],
            definition.c.operation_id == req["operation_id"],
            strict=True,
        ),
        _refuse(
            or_(
                not_(func.coalesce(defin["command_class"] == "pdf", False)),
                req["recipe"].is_distinct_from(defin["recipe"]),
                defin["support_contract"]["effects"][0]["name"].astext.is_distinct_from(
                    "retain_pdf_observations"
                ),
                p_receipt["version"].astext.is_distinct_from("pdf-observation-execution-1"),
                p_receipt["request_id"].astext.is_distinct_from(ctx["request_id"]),
                cast(p_receipt["generation"].astext, BigInteger()).is_distinct_from(
                    ctx["generation"]
                ),
                cast(p_receipt["task_id"].astext, BigInteger()).is_distinct_from(p_task),
                cast(p_receipt["attempt"].astext, BigInteger()).is_distinct_from(p_attempt),
                p_attempt.is_(None),
                p_attempt < 1,
                func.nullif(p_holder, "").is_(None),
                p_receipt["holder"].astext.is_distinct_from(p_holder),
                p_receipt["source_digest"].astext.is_distinct_from(ctx["source_digest"]),
                not_(
                    _exists(
                        runtime,
                        runtime.c.release_id == ctx["release_id"],
                        runtime.c.runtime_id == p_receipt["runtime_id"].astext,
                    )
                ),
            ),
            "observation receipt differs from actual native recognition owner",
        ),
        Assign(
            "profile",
            func.ops.pdf_recognition_profile(
                ctx["release_id"], core_variable("definition", JSONB())
            ),
        ),
        _refuse(
            p_receipt["recipe_digest"].astext.is_distinct_from(
                profile["base_recipe_digest"].astext
            ),
            "observation receipt changes configured recognition recipe",
        ),
        SelectInto(
            select(bindings.c.value).where(bindings.c.value["role"].astext == "capture"),
            ("selected",),
            True,
        ),
        Assign(
            "capture",
            func.ops.ddo_pdf_capture_source_for_request(
                core_variable("request", JSONB()),
                req["project_id"],
                selected["product_id"].astext,
                func.ops.ddo_single_input_support_episode(selected),
                type_=JSONB(),
            )["publication"],
        ),
        Assign(
            "requested",
            func.data.ddo_json(
                func.data.ddo_field(req["binding"]["parameters"], "parameters"), type_=JSONB()
            )["pages"],
        ),
        _refuse(
            or_(requested.is_(None), func.jsonb_typeof(requested) != "array"),
            "observation request lacks its exact physical page selection",
        ),
        SelectInto(
            select(
                func.coalesce(
                    func.jsonb_agg(
                        aggregate_order_by(
                            cast(native.c.scalars_json["page_no"].astext, BigInteger()),
                            cast(native.c.scalars_json["page_no"].astext, BigInteger()),
                        )
                    ),
                    _json([]),
                )
            )
            .select_from(
                record_document.join(
                    membership,
                    and_(
                        membership.c.product_id == record_document.c.product_id,
                        membership.c.revision_id == record_document.c.revision_id,
                        membership.c.parent_id == record_document.c.root_id,
                        membership.c.field_name == "pages",
                    ),
                ).join(
                    native,
                    and_(
                        native.c.product_id == membership.c.product_id,
                        native.c.revision_id == membership.c.revision_id,
                        native.c.record_id == membership.c.record_id,
                    ),
                )
            )
            .where(
                record_document.c.product_id == capture["build_id"].astext,
                record_document.c.revision_id == capture["build_id"].astext,
            ),
            ("available",),
        ),
        If(
            requested == _json([]),
            (Assign("requested", available),),
            (
                _refuse(
                    _exists(numbers, not_(available.contains(_array(numbers.c.value)))),
                    "recognition page is outside the actual selected native inventory",
                ),
            ),
        ),
        _refuse(
            func.jsonb_array_length(p_receipt["pages"]) == 0,
            "observation receipt has no inspected page reports",
        ),
        ForQuery(("page", "page_position"), select(page_rows.c.value, page_rows.c.n), page_steps),
        _refuse(
            groups.is_distinct_from(requested),
            "observation reports do not cover the exact requested page inventory",
        ),
        Return(
            _object(
                "document",
                req["original_source"],
                "source_digest",
                ctx["source_digest"],
                "recipe_digest",
                p_receipt["recipe_digest"],
                "pages",
                pages,
            )
        ),
    )
    locals_ = (
        Local("job", task),
        Local("request", request),
        Local("definition", definition),
        Local("product", product),
        Local("context", pg_type("record")),
        *(
            Local(name, pg_type("jsonb"), _json([]) if name in ("page_groups", "pages") else None)
            for name in values
        ),
        *(
            Local(name, pg_type("bytea"))
            for name in ("report_content", "body_content", "raw_payload")
        ),
        *(Local(name, pg_type("bigint")) for name in ("ordinal", "page_position", "previous_page")),
        Local("previous_outcome", pg_type("text")),
        Local("recovery_count", pg_type("integer"), literal(0)),
    )
    return function(
        "ops",
        "pdf_observation_projection_for_request",
        parameters=(
            Parameter("p_receipt", pg_type("jsonb")),
            Parameter("p_task", column_type(task.c.id)),
            Parameter("p_attempt", column_type(task.c.attempt)),
            Parameter("p_holder", column_type(task.c.claimed_by)),
            Parameter("p_request", pg_type("ops", "data_request")),
        ),
        returns=pg_type("jsonb"),
        body=Block(statements, locals_),
        volatility="stable",
        security_definer=True,
        search_path=("pg_catalog", "pg_temp"),
    )


def observation_publisher_declaration(context, model):
    """Publish the finite decomposed observation with exact input/artifact custody."""
    tables = model.tables
    (
        task,
        definition,
        request,
        product_table,
        body,
        edge,
        artifact,
        owned,
        runtime,
        revoked,
        source,
        revision,
        validation,
        occurrence_table,
        relation_table,
        endpoint_table,
        coverage_table,
        mapping_table,
    ) = (
        tables[name]
        for name in (
            "ops.task",
            "sem.data_operation_definition",
            "ops.data_request",
            "ops.pdf_product",
            "ops.pdf_product_body",
            "ops.pdf_product_input",
            "kb.source_artifact",
            "ops.pdf_product_artifact",
            "sem.runtime_binding",
            "ops.data_revocation",
            "ops.source_build",
            "ops.pdf_published_revision",
            "ops.pdf_build_validation",
            "kb.pdf_occurrence",
            "kb.pdf_relation",
            "kb.pdf_relation_endpoint",
            "kb.pdf_product_coverage",
            "kb.pdf_mapping_report",
        )
    )
    p_task, p_attempt = (core_variable(name, BigInteger()) for name in ("p_task", "p_attempt"))
    p_holder, p_runtime, p_contract = (
        core_variable(name, Text()) for name in ("p_holder", "p_runtime", "p_contract")
    )
    p_payload, p_artifacts = (
        core_variable("p_payload", LargeBinary()),
        core_variable("p_artifacts", ARRAY(LargeBinary())),
    )
    ctx, job, defin, req, previous, pin = (
        _context(model),
        _row("job", task),
        _row("definition", definition),
        _row("native_request", request),
        _row("previous", product_table),
        _row("pin", product_table),
    )
    product, selected, publication, profile = (
        core_variable(name, JSONB())
        for name in ("product", "selected", "publication", "recognition_profile")
    )
    digest, original = core_variable("digest", Text()), core_variable("original", Text())
    wire, field_value = core_variable("wire", JSON()), core_variable("field_value", JSON())
    field_name, field_names = (
        core_variable("field_name", Text()),
        core_variable("envelope_fields", ARRAY(Text())),
    )
    collection_names = ("inputs", "occurrences", "relations", "coverage", "mapping_reports")
    collection_vars = (
        "input_rows",
        "occurrence_rows",
        "relation_rows",
        "coverage_rows",
        "mapping_rows",
    )
    collections = {
        name: core_variable(local, JSON())
        for name, local in zip(collection_names, collection_vars, strict=True)
    }
    item_vars = {
        name: core_variable(name, JSONB())
        for name in ("input", "occurrence", "relation", "endpoint", "coverage", "mapping_report")
    }
    inp, occurrence, relation, endpoint, coverage, mapping = item_vars.values()
    idx, eid = core_variable("idx", BigInteger()), core_variable("eid", BigInteger())
    found = core_variable("found", Boolean())
    fields = (
        func.json_each(wire)
        .table_valued(column("key", Text()), column("value", JSON()))
        .render_derived()
        .alias("fields")
    )
    supplied = _unnest(p_artifacts, "supplied")
    inputs = _rows(collections["inputs"], "inputs", wire=True)
    inputs_ordinal = _rows(collections["inputs"], "inputs_ordinal", wire=True, ordinal=True)
    input_json = cast(inputs.c.value, JSONB())
    recipes = _rows(profile["recipes"], "recipes")
    native_bindings = _rows(req["binding"]["inputs"], "native_bindings")
    observation, image = product["observation"], product["observation"]["image"]
    transform, binding = image["transform"], observation["binding"]

    def context_query(name):
        return select(literal_column("*")).select_from(
            getattr(func.ops, name)(p_task, p_attempt, p_holder)
            if name == "require_pdf_stage_owner"
            else getattr(func.ops, name)(p_task)
        )

    product_pin = and_(
        product_table.c.task_id == p_task,
        product_table.c.product_key == product["product_key"].astext,
    )
    recipe_artifacts = select(_hash(supplied.c.value))
    retained_artifacts = select(owned.c.artifact_digest).where(
        owned.c.task_id == p_task, owned.c.product_key == product["product_key"].astext
    )
    replay_difference = union_all(
        recipe_artifacts.except_(retained_artifacts), retained_artifacts.except_(recipe_artifacts)
    ).subquery("artifact_difference")
    lineage = select(
        cast(publication["task_id"].astext, BigInteger()).label("task_id"),
        publication["product_key"].astext.label("product_key"),
        publication["logical_digest"].astext.label("content_digest"),
    ).cte("lineage", recursive=True)
    lineage = lineage.union(
        select(
            edge.c.input_task_id, edge.c.input_product_key, edge.c.input_content_digest
        ).select_from(
            edge.join(
                lineage,
                and_(
                    edge.c.task_id == lineage.c.task_id, edge.c.product_key == lineage.c.product_key
                ),
            )
        )
    )
    classes = {
        prop.name: prop.range
        for definition_ in context.boundary.definitions
        if definition_.name == "PdfObservationProduct"
        for prop in definition_.properties
    }
    input_context = (
        func.ops.pdf_task_context(pin["task_id"])
        .table_valued(
            column("project_id", request.c.project_id.type), column("source_digest", Text())
        )
        .alias("input_context")
    )
    admitted_revision = revision.join(
        validation,
        and_(
            validation.c.build_id == revision.c.build_id,
            validation.c.frozen_digest == revision.c.frozen_digest,
            validation.c.logical_digest == revision.c.logical_digest,
            validation.c.native_callbacks,
        ),
    )
    resolve_input = (
        *record_shape_steps(context.boundary, classes["inputs"], inp),
        _select_row(
            product_table,
            "pin",
            product_table.c.task_id == cast(inp["task_id"].astext, BigInteger()),
            product_table.c.product_key == inp["product_key"].astext,
            product_table.c.content_digest == inp["content_digest"].astext,
        ),
        _refuse(not_(found), "PDF input pin has no exact admitted product"),
        _refuse(
            and_(pin["task_id"] == p_task, pin["product_key"] == product["product_key"].astext),
            "self PDF input",
        ),
        _refuse(
            or_(
                pin["artifact_digest"] != original,
                not_(
                    _exists(
                        input_context,
                        input_context.c.project_id == ctx["project_id"],
                        input_context.c.source_digest == original,
                    )
                ),
            ),
            "PDF input outside original/project custody",
        ),
        _refuse(
            or_(
                and_(inp["role"].astext == "recognition", pin["kind"] != "recognition_observation"),
                and_(
                    inp["role"].astext == "structural", pin["kind"].not_in(("native", "integrated"))
                ),
            ),
            "PDF input role/kind differs",
        ),
        _refuse(
            or_(
                and_(
                    pin["kind"].in_(("native", "integrated")),
                    not_(
                        _exists(
                            admitted_revision,
                            revision.c.task_id == pin["task_id"],
                            revision.c.product_key == pin["product_key"],
                            revision.c.release_id == pin["release_id"],
                            revision.c.kind == pin["kind"],
                            revision.c.source_digest == original,
                            revision.c.logical_digest == pin["content_digest"],
                            validation.c.contract_digest == pin["contract_digest"],
                            _hash(
                                func.ops.pdf_contract_input(
                                    revision.c.release_id,
                                    "implementation/pdf/docling-validation.schema.json",
                                )
                            )
                            == revision.c.schema_digest,
                        )
                    ),
                ),
                and_(
                    pin["kind"] == "recognition_observation",
                    not_(
                        _exists(
                            body,
                            body.c.task_id == pin["task_id"],
                            body.c.product_key == pin["product_key"],
                            _hash(body.c.payload) == pin["content_digest"],
                            _hash(
                                func.ops.pdf_contract_input(
                                    pin["release_id"], "schema/pdf_products"
                                )
                            )
                            == pin["contract_digest"],
                        )
                    ),
                ),
            ),
            "PDF input has no admitted immutable body",
        ),
    )
    artifact_digests = _unnest(
        array(
            [
                image["artifact_digest"].astext,
                observation["raw_response_digest"].astext,
                observation["mapped_evidence_digest"].astext,
            ],
            type_=Text(),
        ),
        "artifact_digests",
        Text(),
    )
    affine = _rows(transform["affine"], "affine")
    witness = (
        "page_width",
        "page_height",
        "page_rotation",
        "crop_left",
        "crop_top",
        "crop_right",
        "crop_bottom",
        "affine",
    )

    def num(value):
        return cast(value.astext, Numeric())

    def png_dimension(offset):
        return sum(
            cast(func.get_byte(supplied.c.value, offset + n), BigInteger()) * 256 ** (3 - n)
            for n in range(4)
        )

    provider_steps = (
        _refuse(
            or_(not_(product.has_key("observation")), any_(field_names) == "content"),
            "observation body differs",
        ),
        _refuse(
            observation["pass_role"]
            .astext.in_(("chandra_page", "chandra_crop"))
            .is_distinct_from(binding["provider"].astext == "datalab-chandra-2"),
            "Chandra observation role differs from its provider",
        ),
        _refuse(
            observation.has_key("mapped_evidence_digest"),
            "mapped visual evidence requires a supported visual observation",
        ),
        _refuse(
            or_(
                image["precision"].astext.not_in(("unknown", "coarse")),
                transform["status"].astext.not_in(("unknown", "coarse")),
                func.jsonb_typeof(cast(binding["decoding_json"].astext, JSONB())).is_distinct_from(
                    "object"
                ),
                and_(
                    observation.has_key("usage_json"),
                    func.jsonb_typeof(
                        cast(observation["usage_json"].astext, JSONB())
                    ).is_distinct_from("object"),
                ),
            ),
            "unadmitted provider transform/precision/settings",
        ),
        _refuse(
            not_(
                _exists(
                    supplied,
                    _hash(supplied.c.value) == image["artifact_digest"].astext,
                    func.octet_length(supplied.c.value) >= 24,
                    func.substr(supplied.c.value, 1, 8) == func.decode("89504e470d0a1a0a", "hex"),
                    png_dimension(16) == cast(image["width"].astext, BigInteger()),
                    png_dimension(20) == cast(image["height"].astext, BigInteger()),
                )
            ),
            "submitted PNG dimensions/bytes differ",
        ),
        _refuse(
            or_(
                and_(
                    observation["outcome"].astext.in_(("succeeded", "partial")),
                    not_(observation.has_key("raw_response_digest")),
                ),
                and_(
                    observation["outcome"].astext.in_(("failed", "unknown", "unsupported")),
                    func.coalesce(observation["diagnostic"].astext, "") == "",
                ),
                product["health"]["execution_outcome"].astext.is_distinct_from(
                    observation["outcome"].astext
                ),
                (observation["usage_availability"].astext == "available").is_distinct_from(
                    observation.has_key("usage_json")
                ),
            ),
            "observation response/diagnostic/usage availability differs",
        ),
        _refuse(
            and_(
                transform["status"].astext == "unknown",
                transform.has_any(array(list(witness), type_=Text())),
            ),
            "unknown transform carries fabricated parameters",
        ),
        _refuse(
            and_(
                transform["status"].astext == "coarse",
                or_(
                    not_(transform.has_all(array(list(witness), type_=Text()))),
                    func.jsonb_array_length(transform["affine"]) != 6,
                    _exists(affine, func.jsonb_typeof(affine.c.value) != "number"),
                    cast(transform["page_rotation"].astext, BigInteger()).not_in((0, 90, 180, 270)),
                    not_(
                        and_(
                            num(transform["crop_left"]) >= 0,
                            num(transform["crop_left"]) < num(transform["crop_right"]),
                            num(transform["crop_right"]) <= num(transform["page_width"]),
                            num(transform["crop_top"]) >= 0,
                            num(transform["crop_top"]) < num(transform["crop_bottom"]),
                            num(transform["crop_bottom"]) <= num(transform["page_height"]),
                        )
                    ),
                ),
            ),
            "coarse transform requires complete page/crop/rotation witness",
        ),
        _refuse(
            _exists(
                artifact_digests,
                artifact_digests.c.value.is_not(None),
                not_(_exists(supplied, _hash(supplied.c.value) == artifact_digests.c.value)),
            ),
            "observation artifact bytes are missing",
        ),
        _refuse(
            not_(_exists(supplied, _hash(supplied.c.value) == product["recipe_digest"].astext)),
            "PDF recipe bytes are missing",
        ),
    )
    occurrence_rows = _rows(collections["occurrences"], "occurrence_rows", wire=True)
    region = occurrence["region"]
    coordinate_rows = (
        func.jsonb_each(region)
        .table_valued(column("key", Text()), column("value", JSONB()))
        .render_derived()
        .alias("coordinates")
    )
    occurrence_steps = (
        *record_shape_steps(context.boundary, classes["occurrences"], occurrence),
        _refuse(
            or_(
                occurrence["occurrence_id"].astext == "",
                occurrence.has_key("start") != occurrence.has_key("end"),
                and_(
                    occurrence.has_key("start"),
                    or_(
                        cast(occurrence["start"].astext, BigInteger())
                        > cast(occurrence["end"].astext, BigInteger()),
                        occurrence["address_space"].astext.not_in(
                            ("native_item", "recognized_text", "selected_item", "raw_response")
                        ),
                        occurrence["precision"].astext.in_(
                            ("unknown", "coarse", "block", "inherited")
                        ),
                        and_(
                            occurrence.has_key("text"),
                            cast(occurrence["end"].astext, BigInteger())
                            > func.char_length(occurrence["text"].astext),
                        ),
                    ),
                ),
            ),
            "unqualified PDF occurrence address/range",
        ),
        _refuse(
            and_(
                occurrence.has_key("region"),
                or_(
                    num(region["left"]) > num(region["right"]),
                    and_(
                        region["origin"].astext == "top_left",
                        num(region["top"]) > num(region["bottom"]),
                    ),
                    and_(
                        region["origin"].astext == "bottom_left",
                        num(region["top"]) < num(region["bottom"]),
                    ),
                ),
            ),
            "region coordinate origin/bounds differ",
        ),
        _refuse(
            and_(
                occurrence.has_key("region"),
                or_(
                    region["precision"].astext.not_in(("unknown", "coarse", "block")),
                    region["address_space"].astext.not_in(("submitted_pixels", "normalized_raw")),
                    and_(
                        region["address_space"].astext == "submitted_pixels",
                        or_(
                            region["origin"].astext != "top_left",
                            num(region["left"]) < 0,
                            num(region["right"]) > num(image["width"]),
                            num(region["top"]) < 0,
                            num(region["bottom"]) > num(image["height"]),
                        ),
                    ),
                    and_(
                        region["address_space"].astext == "normalized_raw",
                        _exists(
                            coordinate_rows,
                            coordinate_rows.c.key.in_(("left", "top", "right", "bottom")),
                            or_(
                                cast(cast(coordinate_rows.c.value, Text()), Numeric()) < 0,
                                cast(cast(coordinate_rows.c.value, Text()), Numeric()) > 1,
                            ),
                        ),
                    ),
                ),
            ),
            "provider region precision/frame/bounds differs",
        ),
        _refuse(
            and_(
                occurrence.has_key("page_no"),
                occurrence["page_no"].astext.is_distinct_from(image["page_no"].astext),
            ),
            "observation page differs from submitted image",
        ),
        _refuse(
            occurrence["precision"].astext.not_in(("unknown", "coarse", "block")),
            "I10/I11 provider precision is unadmitted",
        ),
        Sql(
            insert(occurrence_table).values(
                task_id=p_task,
                product_key=product["product_key"].astext,
                occurrence_id=occurrence["occurrence_id"].astext,
                kind=occurrence["kind"].astext,
                address_space=occurrence["address_space"].astext,
                precision=occurrence["precision"].astext,
                body=occurrence,
                pointer=occurrence["pointer"].astext,
            )
        ),
    )
    endpoints = _rows(relation["endpoints"], "endpoints")
    endpoints_ordinal = _rows(relation["endpoints"], "endpoints_ordinal", ordinal=True)
    endpoint_pin = edge.join(
        product_table,
        and_(
            product_table.c.task_id == edge.c.input_task_id,
            product_table.c.product_key == edge.c.input_product_key,
            product_table.c.content_digest == edge.c.input_content_digest,
        ),
    )
    endpoint_steps = (
        If(
            endpoint.has_key("input_index"),
            (
                SelectInto(
                    select(core_relation_row(product_table))
                    .select_from(endpoint_pin)
                    .where(
                        edge.c.task_id == p_task,
                        edge.c.product_key == product["product_key"].astext,
                        edge.c.input_index == cast(endpoint["input_index"].astext, BigInteger()),
                    ),
                    ("pin",),
                ),
                _refuse(
                    or_(not_(found), endpoint["role"].astext == "output"),
                    "PDF endpoint input index/role differs",
                ),
            ),
            (
                _refuse(endpoint["role"].astext != "output", "local PDF endpoint must be output"),
                _select_row(product_table, "pin", product_pin, strict=True),
            ),
        ),
        Sql(
            insert(endpoint_table).values(
                task_id=p_task,
                product_key=product["product_key"].astext,
                relation_id=relation["relation_id"].astext,
                endpoint_index=eid,
                role=endpoint["role"].astext,
                target_task_id=pin["task_id"],
                target_product_key=pin["product_key"],
                target_content_digest=pin["content_digest"],
                occurrence_id=endpoint["occurrence_id"].astext,
            )
        ),
    )
    relation_rows = _rows(collections["relations"], "relation_rows", wire=True)
    relation_steps = (
        *record_shape_steps(context.boundary, classes["relations"], relation),
        _refuse(
            or_(
                relation["relation_id"].astext == "",
                relation["policy"].astext == "",
                relation["evidence"].astext == "",
                and_(
                    relation["kind"].astext == "correspondence",
                    relation["outcome"].astext.not_in(
                        ("matched", "ambiguous", "unmatched", "unresolved")
                    ),
                ),
                and_(
                    relation["kind"].astext == "decision",
                    relation["outcome"].astext.not_in(
                        (
                            "selected",
                            "added",
                            "replaced",
                            "retained_alternative",
                            "rejected",
                            "unresolved",
                        )
                    ),
                ),
            ),
            "PDF relation kind/outcome/policy differs",
        ),
        _refuse(
            or_(
                not_(_exists(endpoints, endpoints.c.value.has_key("input_index"))),
                and_(
                    relation["kind"].astext == "correspondence",
                    relation["outcome"].astext.in_(("matched", "ambiguous")),
                    select(
                        func.count(
                            func.distinct(
                                tuple_(
                                    endpoints.c.value["input_index"].astext,
                                    endpoints.c.value["occurrence_id"].astext,
                                )
                            )
                        )
                    ).scalar_subquery()
                    < 2,
                ),
                and_(
                    relation["kind"].astext == "decision",
                    relation["outcome"].astext.in_(("selected", "added", "replaced")),
                    not_(_exists(endpoints, endpoints.c.value["role"].astext == "output")),
                ),
                and_(
                    relation["kind"].astext == "decision",
                    relation["outcome"].astext == "rejected",
                    _exists(endpoints, endpoints.c.value["role"].astext == "output"),
                ),
            ),
            "PDF relation endpoint set differs",
        ),
        _refuse(
            select(func.count()).select_from(endpoints).scalar_subquery()
            != select(
                func.count(
                    func.distinct(
                        tuple_(
                            endpoints.c.value["input_index"].astext,
                            endpoints.c.value["occurrence_id"].astext,
                            endpoints.c.value["role"].astext,
                        )
                    )
                )
            ).scalar_subquery(),
            "duplicate PDF relation endpoint",
        ),
        Sql(
            insert(relation_table).values(
                task_id=p_task,
                product_key=product["product_key"].astext,
                relation_id=relation["relation_id"].astext,
                kind=relation["kind"].astext,
                body=relation.op("-", return_type=JSONB())("endpoints"),
            )
        ),
        ForQuery(
            ("endpoint", "eid"),
            select(endpoints_ordinal.c.value, endpoints_ordinal.c.n - 1),
            endpoint_steps,
        ),
    )
    mappings = _rows(
        func.coalesce(collections["mapping_reports"], cast(literal("[]"), JSON())),
        "mappings",
        wire=True,
        ordinal=True,
    )
    mapping_value = cast(mappings.c.value, JSONB())
    mapping_joins = mappings.outerjoin(
        edge,
        and_(
            edge.c.task_id == p_task,
            edge.c.product_key == product["product_key"].astext,
            edge.c.input_index == cast(mapping_value["input_index"].astext, BigInteger()),
        ),
    )
    supports = _rows(coverage["supports"], "supports")
    support_joins = supports.join(
        edge,
        and_(
            edge.c.task_id == p_task,
            edge.c.product_key == product["product_key"].astext,
            edge.c.input_index == cast(supports.c.value["input_index"].astext, BigInteger()),
        ),
    ).join(
        coverage_table,
        and_(
            coverage_table.c.task_id == edge.c.input_task_id,
            coverage_table.c.product_key == edge.c.input_product_key,
            coverage_table.c.coverage_id == supports.c.value["coverage_id"].astext,
        ),
    )
    missing_support_joins = supports.outerjoin(
        edge,
        and_(
            edge.c.task_id == p_task,
            edge.c.product_key == product["product_key"].astext,
            edge.c.input_index == cast(supports.c.value["input_index"].astext, BigInteger()),
        ),
    ).outerjoin(
        coverage_table,
        and_(
            coverage_table.c.task_id == edge.c.input_task_id,
            coverage_table.c.product_key == edge.c.input_product_key,
            coverage_table.c.coverage_id == supports.c.value["coverage_id"].astext,
        ),
    )
    coverage_rows = _rows(collections["coverage"], "coverage_rows", wire=True)
    coverage_steps = (
        *record_shape_steps(context.boundary, classes["coverage"], coverage),
        _refuse(
            or_(
                *(
                    coverage[name].astext == ""
                    for name in ("coverage_id", "scope", "family", "discovery_policy", "detail")
                ),
                coverage["outcome"].astext == "complete",
            ),
            "PDF coverage scope/policy/outcome differs",
        ),
        _refuse(
            or_(
                _exists(
                    missing_support_joins,
                    or_(
                        coverage_table.c.coverage_id.is_(None),
                        coverage_table.c.body["scope"].astext.is_distinct_from(
                            coverage["scope"].astext
                        ),
                        coverage_table.c.body["family"].astext.is_distinct_from(
                            coverage["family"].astext
                        ),
                    ),
                ),
                and_(
                    coverage["outcome"].astext == "complete",
                    not_(
                        _exists(
                            support_joins,
                            coverage_table.c.body["scope"].astext == coverage["scope"].astext,
                            coverage_table.c.body["family"].astext == coverage["family"].astext,
                            coverage_table.c.body["outcome"].astext == "complete",
                        )
                    ),
                ),
            ),
            "complete coverage lacks qualified scope/family input attribution",
        ),
        Sql(
            insert(coverage_table).values(
                task_id=p_task,
                product_key=product["product_key"].astext,
                coverage_id=coverage["coverage_id"].astext,
                body=coverage,
            )
        ),
    )
    statements = (
        _select_row(task, "job", task.c.id == p_task, strict=True),
        SelectInto(context_query("pdf_task_context"), ("context",), True),
        SelectInto(
            select(core_relation_row(definition))
            .select_from(
                definition.join(
                    request,
                    and_(
                        request.c.release_id == definition.c.release_id,
                        request.c.operation_id == definition.c.operation_id,
                    ),
                )
            )
            .where(request.c.id == ctx["request_id"]),
            ("definition",),
            True,
        ),
        _refuse(
            or_(
                not_(func.coalesce(defin["command_class"] == "pdf", False)),
                defin["support_contract"]["effects"][0]["name"].astext.is_distinct_from(
                    "retain_pdf_observations"
                ),
            ),
            "native observations require the exact approved PDF recognition effect",
        ),
        _refuse(
            or_(
                job["attempt"].is_distinct_from(p_attempt),
                job["claimed_by"].is_distinct_from(p_holder),
            ),
            "stale recognition observation attempt",
            "P0004",
        ),
        Perform(func.sem.require_runtime_binding(ctx["release_id"], p_runtime)),
        _refuse(
            or_(
                not_(
                    _exists(
                        runtime,
                        runtime.c.release_id == ctx["release_id"],
                        runtime.c.runtime_id == p_runtime,
                        _decode(runtime.c.manifest_bytes)["execution_profile"].astext
                        == select(request.c.binding["execution_profile"].astext)
                        .where(request.c.id == ctx["request_id"])
                        .scalar_subquery(),
                    )
                ),
                _exists(
                    revoked,
                    revoked.c.scope
                    == func.ops.ddo_scope(
                        ctx["project_id"],
                        select(request.c.original_source)
                        .where(request.c.id == ctx["request_id"])
                        .scalar_subquery(),
                    ),
                    revoked.c.selector_kind == "runtime",
                    revoked.c.selector == p_runtime,
                ),
            ),
            "observation publisher runtime differs from admitted request profile/trust",
        ),
        Assign("wire", _decode(p_payload, wire=True)),
        _refuse(
            or_(
                func.json_typeof(wire).is_distinct_from("object"),
                wire["kind"].astext.is_distinct_from("recognition_observation"),
            ),
            "parsing record must be an object: PdfIntegratedProduct",
        ),
        ForQuery(
            ("field_name", "field_value"),
            select(fields.c.key, fields.c.value),
            (
                Assign("envelope_fields", func.array_append(field_names, field_name)),
                If(
                    field_name == "content",
                    (Raise("document content is not an observation", "23514"),),
                ),
                *(
                    If(field_name == name, (Assign(local, field_value),))
                    for name, local in zip(collection_names, collection_vars, strict=True)
                ),
                If(
                    field_name.not_in((*collection_names, "content")),
                    (
                        Assign(
                            "product",
                            product.concat(_object(field_name, cast(field_value, JSONB()))),
                        ),
                    ),
                ),
            ),
        ),
        *record_shape_steps(
            context.boundary,
            "PdfObservationProduct",
            product,
            fields=collections,
            field_names=field_names,
            deferred_arrays=frozenset(collection_names),
        ),
        _refuse(
            or_(
                product["kind"].astext.is_distinct_from("recognition_observation"),
                product["product_key"].astext == "",
            ),
            "recognition observation kind/key/health differs",
        ),
        Assign(
            "recognition_profile",
            func.ops.pdf_recognition_profile(
                ctx["release_id"], core_variable("definition", JSONB())
            ),
        ),
        _refuse(
            not_(
                _exists(
                    recipes,
                    recipes.c.value["digest"].astext == product["recipe_digest"].astext,
                    recipes.c.value["weights_digest"].astext == binding["weights_digest"].astext,
                    recipes.c.value["tokenizer_digest"].astext
                    == binding["tokenizer_digest"].astext,
                )
            ),
            "recognition recipe/model differs from exact admitted profile",
        ),
        _refuse(
            _hash(
                func.ops.pdf_contract_input(ctx["release_id"], "schema/pdf_products")
            ).is_distinct_from(p_contract),
            "PDF contract is not archived by task release",
        ),
        _refuse(
            observation["pass_role"].astext.in_(("chandra_page", "chandra_crop")),
            "native integration cannot publish legacy Chandra observations",
        ),
        SelectInto(
            select(source.c.artifact_digest).where(
                source.c.task_id == p_task, source.c.release_id == ctx["release_id"]
            ),
            ("original",),
        ),
        _refuse(not_(found), "owned PDF original was not retained"),
        _refuse(
            product["artifact_digest"].astext.is_distinct_from(original),
            "PDF original custody differs",
        ),
        _select_row(product_table, "previous", product_pin),
        If(
            not_(found),
            (
                SelectInto(context_query("require_pdf_stage_owner"), ("context",), True),
                _select_row(task, "job", task.c.id == p_task, strict=True),
                _select_row(product_table, "previous", product_pin),
            ),
            (_select_row(task, "job", task.c.id == p_task, strict=True, lock=True),),
        ),
        _refuse(
            or_(
                job["attempt"].is_distinct_from(p_attempt),
                job["claimed_by"].is_distinct_from(p_holder),
            ),
            "stale recognition observation attempt",
            "P0004",
        ),
        If(
            previous["task_id"].is_not(None),
            (
                _refuse(
                    or_(
                        previous["content_digest"] != digest,
                        previous["contract_digest"] != p_contract,
                        previous["kind"] != product["kind"].astext,
                        not_(
                            _exists(
                                body,
                                body.c.task_id == p_task,
                                body.c.product_key == product["product_key"].astext,
                                body.c.payload == p_payload,
                            )
                        ),
                    ),
                    "immutable PDF bundle replay differs",
                ),
                _refuse(
                    or_(
                        _exists(replay_difference),
                        _exists(
                            supplied,
                            not_(
                                _exists(
                                    artifact,
                                    artifact.c.artifact_digest == _hash(supplied.c.value),
                                    artifact.c.content == supplied.c.value,
                                )
                            ),
                        ),
                    ),
                    "PDF replay artifacts differ",
                ),
                Return(digest),
            ),
        ),
        Perform(func.ops.require_pdf_operation(ctx["release_id"], "publish_pdf_observation")),
        _refuse(
            original.is_distinct_from(ctx["source_digest"]),
            "native recognition original differs from the owned request source",
        ),
        _select_row(request, "native_request", request.c.id == ctx["request_id"], strict=True),
        SelectInto(
            select(native_bindings.c.value).where(
                native_bindings.c.value["role"].astext == "capture"
            ),
            ("selected",),
            True,
        ),
        _refuse(
            or_(
                selected["member_id"].astext.is_not(None),
                func.ops.ddo_single_input_support_episode(selected).is_(None),
            ),
            "native recognition requires one whole selected PDF support",
        ),
        Assign(
            "publication",
            func.ops.ddo_pdf_capture_source(
                req["id"],
                ctx["project_id"],
                selected["product_id"].astext,
                func.ops.ddo_single_input_support_episode(selected),
                type_=JSONB(),
            )["publication"],
        ),
        _refuse(
            or_(
                select(func.count())
                .select_from(inputs)
                .where(input_json["role"].astext == "structural")
                .scalar_subquery()
                != 1,
                not_(
                    _exists(
                        inputs,
                        input_json["role"].astext == "structural",
                        input_json["task_id"].astext == publication["task_id"].astext,
                        input_json["product_key"].astext == publication["product_key"].astext,
                        input_json["content_digest"].astext == publication["logical_digest"].astext,
                    )
                ),
            ),
            "native recognition structural input differs from exact selected PDF publication",
        ),
        _refuse(
            select(1)
            .select_from(inputs)
            .where(
                input_json["role"].astext == "recognition",
                cast(input_json["task_id"].astext, BigInteger()) != p_task,
                not_(
                    _exists(
                        lineage,
                        lineage.c.task_id == cast(input_json["task_id"].astext, BigInteger()),
                        lineage.c.product_key == input_json["product_key"].astext,
                        lineage.c.content_digest == input_json["content_digest"].astext,
                    )
                ),
            )
            .exists(),
            "native recognition input is outside exact selected publication lineage",
        ),
        ForQuery(
            ("input", "idx"),
            select(cast(inputs_ordinal.c.value, JSONB()), inputs_ordinal.c.n - 1),
            resolve_input,
        ),
        _refuse(
            select(func.count()).select_from(inputs).scalar_subquery()
            != select(
                func.count(
                    func.distinct(
                        tuple_(
                            input_json["role"].astext,
                            input_json["task_id"].astext,
                            input_json["product_key"].astext,
                        )
                    )
                )
            ).scalar_subquery(),
            "duplicate PDF input role/pin",
        ),
        *provider_steps,
        Sql(
            insert(artifact)
            .from_select(
                ("artifact_digest", "content"), select(_hash(supplied.c.value), supplied.c.value)
            )
            .on_conflict_do_nothing()
        ),
        Sql(
            insert(product_table).values(
                task_id=p_task,
                product_key=product["product_key"].astext,
                content_digest=digest,
                kind=product["kind"].astext,
                artifact_digest=original,
                release_id=ctx["release_id"],
                contract_digest=p_contract,
                publication_context=_object(
                    "version",
                    "pdf-observation-publication-1",
                    "request_id",
                    ctx["request_id"],
                    "generation",
                    ctx["generation"],
                    "task_id",
                    p_task,
                    "attempt",
                    p_attempt,
                    "holder",
                    p_holder,
                    "runtime_id",
                    p_runtime,
                    "release_id",
                    ctx["release_id"],
                    "source_digest",
                    original,
                ),
            )
        ),
        Sql(
            insert(owned)
            .from_select(
                ("task_id", "product_key", "artifact_digest"),
                select(p_task, product["product_key"].astext, _hash(supplied.c.value)),
            )
            .on_conflict_do_nothing()
        ),
        Sql(
            insert(body).values(
                task_id=p_task,
                product_key=product["product_key"].astext,
                payload=p_payload,
                recipe_digest=product["recipe_digest"].astext,
                descriptor=product,
            )
        ),
        Sql(
            insert(edge).from_select(
                (
                    "task_id",
                    "product_key",
                    "input_index",
                    "role",
                    "input_task_id",
                    "input_product_key",
                    "input_content_digest",
                ),
                select(
                    p_task,
                    product["product_key"].astext,
                    inputs_ordinal.c.n - 1,
                    inputs_ordinal.c.value["role"].astext,
                    cast(inputs_ordinal.c.value["task_id"].astext, BigInteger()),
                    inputs_ordinal.c.value["product_key"].astext,
                    inputs_ordinal.c.value["content_digest"].astext,
                ),
            )
        ),
        ForQuery(("occurrence",), select(cast(occurrence_rows.c.value, JSONB())), occurrence_steps),
        ForQuery(("relation",), select(cast(relation_rows.c.value, JSONB())), relation_steps),
        _refuse(
            _exists(
                mapping_joins,
                or_(
                    edge.c.role.is_distinct_from("recognition"),
                    and_(
                        mapping_value["outcome"].astext != "mapped",
                        func.coalesce(mapping_value["reason"].astext, "") == "",
                    ),
                    and_(
                        mapping_value.has_key("occurrence_id"),
                        not_(
                            _exists(
                                occurrence_table,
                                occurrence_table.c.task_id == edge.c.input_task_id,
                                occurrence_table.c.product_key == edge.c.input_product_key,
                                occurrence_table.c.occurrence_id
                                == mapping_value["occurrence_id"].astext,
                            )
                        ),
                    ),
                ),
            ),
            "mapping disposition differs from recognition custody",
        ),
        ForQuery(
            ("mapping_report", "idx"),
            select(cast(mappings.c.value, JSONB()), mappings.c.n - 1),
            (
                *record_shape_steps(context.boundary, classes["mapping_reports"], mapping),
                Sql(
                    insert(mapping_table).values(
                        task_id=p_task,
                        product_key=product["product_key"].astext,
                        report_index=idx,
                        input_index=cast(mapping["input_index"].astext, BigInteger()),
                        body=mapping,
                    )
                ),
            ),
        ),
        _refuse(func.json_array_length(collections["coverage"]) == 0, "PDF coverage is mandatory"),
        ForQuery(("coverage",), select(cast(coverage_rows.c.value, JSONB())), coverage_steps),
        Return(digest),
    )
    calls = [
        call
        for owner, call in pdf_call_bindings(context.domain)
        if owner == "publish_pdf_observation" and call.id == "publish_pdf_observation"
    ]
    if len(calls) != 1:
        raise ValueError("observation publication requires its one resolved native call")
    binding_ = calls[0]
    expected_parameters = (
        "p_task",
        "p_attempt",
        "p_holder",
        "p_runtime",
        "p_contract",
        "p_payload",
        "p_artifacts",
    )
    if (
        binding_.symbol != "ops.publish_pdf_observation"
        or binding_.backend != "native"
        or binding_.cardinality != "one"
        or binding_.result_mode != "scalar"
        or tuple(field.native_parameter for field in binding_.parameters) != expected_parameters
        or len(binding_.result_fields) != 1
        or binding_.result_fields[0].resolved is None
        or binding_.result_fields[0].resolved.kind != "string"
    ):
        raise ValueError("observation publication call differs from its supported program")
    parameters = []
    for field in binding_.parameters:
        resolved = field.resolved
        if resolved is None or resolved.kind not in field_kinds() or field.native_parameter is None:
            raise ValueError("observation publication has an unresolved native field")
        kind = pg_type(field_kinds()[resolved.kind].postgres)
        if resolved.multivalued:
            kind.arrayBounds = (ast.Integer(ival=-1),)
        parameters.append(Parameter(field.native_parameter, kind))
    text_array = pg_type("text")
    text_array.arrayBounds = (ast.Integer(ival=-1),)
    locals_ = (
        Local("job", task),
        Local("context", pg_type("record")),
        Local("definition", definition),
        Local("native_request", request),
        Local("previous", product_table),
        Local("pin", product_table),
        Local("product", pg_type("jsonb"), _json({})),
        Local("digest", pg_type("text"), _hash(p_payload)),
        Local("original", pg_type("text")),
        Local("wire", pg_type("json")),
        Local("field_name", pg_type("text")),
        Local("field_value", pg_type("json")),
        Local("envelope_fields", text_array, array([], type_=Text())),
        *(Local(name, pg_type("json")) for name in collection_vars),
        *(
            Local(name, pg_type("jsonb"))
            for name in (*item_vars, "selected", "publication", "recognition_profile")
        ),
        Local("idx", pg_type("bigint")),
        Local("eid", pg_type("bigint")),
    )
    return function(
        "ops",
        "publish_pdf_observation",
        parameters=tuple(parameters),
        returns=pg_type("text"),
        body=Block(statements, locals_),
        security_definer=True,
        search_path=("pg_catalog", "pg_temp"),
    )
