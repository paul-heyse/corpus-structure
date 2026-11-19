"""Forward native publication over immutable PDF records and typed companions."""

from __future__ import annotations

import json
from collections.abc import Mapping

from pglast import ast, enums
from sqlalchemy import MetaData, Table, Text, case, cast, func, null, select, union_all
from sqlalchemy.dialects.postgresql import JSONB, Insert, array, dialect, insert

from corpus_structure.schema.integrity import role_name

from .metadata import get_metadata as default_metadata
from .native_call_contracts import OperationCallBinding
from .native_objects import (
    INTERNAL_PROGRAM,
    NativeProgramAccess,
    native_privilege_sql,
    native_sql_script,
)
from .native_program import (
    NativeRoutine,
    Parameter,
    column_type,
    core_cast_literal,
    core_reference,
    core_variable,
    pg_type,
)
from .native_program_registry import ProgramDeclaration
from .pdf_staging import STAGE_FAMILIES
from .prepared_sql import prepare_sql

_FINAL = {
    "header": "ops.pdf_record_document",
    "artifact_stream": "ops.pdf_artifact_stream",
    "native": "kb.pdf_record_native",
    "membership": "kb.pdf_record_membership",
    "reference": "kb.pdf_record_reference",
    "companion": "kb.pdf_record_companion",
    "endpoint": "kb.pdf_record_endpoint",
    "companion_field": "kb.pdf_record_companion_field",
    "access": "kb.pdf_record_access",
    "region": "kb.pdf_record_region",
}


def _prepare_pdf_copy_statements(
    metadata: MetaData, stages: Mapping[str, str], *, build_parameter: str
) -> tuple[Insert, ...]:
    """Copy frozen families using their model-owned physical columns and relations."""
    native = metadata.tables[_FINAL["native"]]
    artifacts = metadata.tables[_FINAL["artifact_stream"]]
    build = core_variable(build_parameter, native.c.product_id.type)
    statements = []
    for family, relation in _FINAL.items():
        target = metadata.tables[relation]
        source = metadata.tables[stages[family]].alias("s")
        values = [
            _prepare_pdf_reference_target(source, native, artifacts, build)
            if family == "reference" and column.key == "target_id"
            else source.c[column.key]
            for column in target.columns
        ]
        statements.append(
            insert(target)
            .from_select(
                [column.key for column in target.columns],
                select(*values).where(source.c.product_id == build),
            )
            .on_conflict_do_nothing()
        )
    return tuple(statements)


def _prepare_pdf_reference_target(source, native: Table, artifacts: Table, build):
    """Resolve exact native addresses without losing scalar ambiguity failures."""
    # Materialize overflow keys once. Fresh products have no planner statistics,
    # so an inline miss must not rescan all native rows for every reference.
    streamed = (
        select(native.c.record_id, artifacts.c.byte_length, artifacts.c.byte_root)
        .select_from(
            native.join(
                artifacts,
                (artifacts.c.product_id == native.c.product_id)
                & (artifacts.c.revision_id == native.c.revision_id)
                & (artifacts.c.stream_id == native.c.native_address_stream_id),
            )
        )
        .where(
            native.c.product_id == build,
            native.c.revision_id == build,
            native.c.native_address.is_(None),
        )
        .cte("streamed_targets")
        .prefix_with("MATERIALIZED", dialect="postgresql")
    )
    origin = native.alias("source")
    source_address = (
        select(origin.c.native_address)
        .where(
            origin.c.product_id == build,
            origin.c.revision_id == build,
            origin.c.record_id == source.c.source_id,
        )
        .correlate(source)
        .scalar_subquery()
    )
    graph_cell = (
        select(native.c.record_id)
        .where(
            native.c.product_id == build,
            native.c.revision_id == build,
            native.c.native_type == "GraphCell",
            native.c.scalars_json["cell_id"].astext == source.c.native_pointer,
            func.regexp_replace(native.c.native_address, "/cells/[0-9]+$", "")
            == func.regexp_replace(source_address, "/links/[0-9]+$", ""),
        )
        .correlate(source)
        .scalar_subquery()
    )
    pointer_bytes = func.convert_to(source.c.native_pointer, "UTF8")
    addressed = union_all(
        select(native.c.record_id)
        .where(
            native.c.product_id == build,
            native.c.revision_id == build,
            native.c.native_address == source.c.native_pointer,
        )
        .correlate(source),
        select(streamed.c.record_id)
        .where(
            streamed.c.byte_length == func.octet_length(pointer_bytes),
            streamed.c.byte_root
            == func.encode(func.ops.pdf_identity_byte_root(pointer_bytes), "hex"),
        )
        .correlate(source),
    ).subquery("target")
    # Keep the scalar subquery around UNION ALL: an inline/streamed collision
    # must fail rather than select an arbitrary target or multiply copied rows.
    inline = select(addressed.c.record_id).correlate(source).scalar_subquery()
    overflow = (
        select(native.c.record_id)
        .where(
            native.c.product_id == build,
            native.c.revision_id == build,
            func.ops.pdf_reference_bytes_equal(
                build,
                build,
                native.c.native_address,
                native.c.native_address_stream_id,
                source.c.native_pointer,
                source.c.native_pointer_stream_id,
            ),
        )
        .correlate(source)
        .scalar_subquery()
    )
    return func.coalesce(
        source.c.target_id,
        case(
            (source.c.field_name.in_(("source_cell_id", "target_cell_id")), graph_cell),
            (source.c.native_pointer_stream_id.is_(None), inline),
            else_=overflow,
        ),
    )


def _prepare_pdf_build_program(
    metadata: MetaData, stages: Mapping[str, str], binding: OperationCallBinding
) -> ProgramDeclaration:
    from .native_program import (
        Assign,
        Block,
        Local,
        Perform,
        Sql,
        call,
        literal,
        variable,
        void_call_routine,
    )

    names = {}
    for field in binding.parameters:
        if field.native_parameter is None:
            raise ValueError(f"{binding.id}.{field.name}: missing native parameter")
        names[field.name] = field.native_parameter
    frozen = call(
        "ops",
        "require_pdf_frozen",
        *(
            variable(names[name])
            for name in ("build_id", "task_id", "attempt", "holder", "frozen_digest")
        ),
    )
    routine = void_call_routine(
        binding,
        security_definer=True,
        search_path=("pg_catalog", "pg_temp"),
        body=Block(
            locals=(Local("b", metadata.tables["ops.pdf_stage_build"]),),
            statements=(
                Assign("b", frozen),
                Perform(
                    call(
                        "ops",
                        "require_pdf_operation",
                        variable("b", "release_id"),
                        literal("prepare_pdf_build"),
                    )
                ),
                *(
                    Sql(statement)
                    for statement in _prepare_pdf_copy_statements(
                        metadata, stages, build_parameter=names["build_id"]
                    )
                ),
                Perform(frozen),
            ),
        ),
    )

    return _publication_program(routine)


def _schema_json(schema: dict) -> str:
    """Emit the released metadata schema's exact integral numeric bounds."""
    from decimal import Decimal

    def exact_number(value):
        if isinstance(value, Decimal) and value.is_finite() and value == value.to_integral_value():
            return int(value)
        raise TypeError("metadata JSON Schema has a non-integral/non-JSON numeric bound")

    return json.dumps(schema, default=exact_number, ensure_ascii=False, separators=(",", ":"))


def _coverage_support_violation_statement(*, target_metadata=None):
    """Set-shaped resolution of the existing exact-pin support/complete rule."""
    metadata = default_metadata() if target_metadata is None else target_metadata
    from sqlalchemy import (
        and_,
        cast,
        column,
        false,
        func,
        literal,
        or_,
        select,
        true,
        union_all,
    )
    from sqlalchemy.dialects.postgresql import JSONB

    companion = metadata.tables["kb.pdf_record_companion"]
    frozen = metadata.tables["ops.pdf_frozen_build"]
    pin = metadata.tables["ops.pdf_product"].alias("support_pin")
    publication = metadata.tables["ops.pdf_published_revision"].alias("support_publication")
    retained = metadata.tables["kb.pdf_product_coverage"].alias("retained_coverage")
    input_ = companion.alias("support_input")
    recorded = companion.alias("recorded_coverage")
    build = core_reference("p_build", type_=companion.c.product_id.type)
    claims = (
        select(
            companion.c.local_id.label("claim_id"),
            companion.c.body,
            frozen.c.kind.label("product_kind"),
        )
        .select_from(companion.join(frozen, frozen.c.build_id == companion.c.product_id))
        .where(
            companion.c.product_id == build,
            companion.c.revision_id == build,
            companion.c.family == "coverage",
        )
        .cte("coverage_claims")
        .prefix_with("MATERIALIZED", dialect="postgresql")
    )
    support = (
        func.jsonb_array_elements(
            func.coalesce(
                func.nullif(
                    claims.c.body["supports"], core_cast_literal("null", pg_type("jsonb"), JSONB())
                ),
                core_cast_literal("[]", pg_type("jsonb"), JSONB()),
            )
        )
        .table_valued(column("value", JSONB))
        .lateral("support")
    )
    edges = (
        select(
            claims.c.claim_id,
            claims.c.body["scope"].astext.label("scope"),
            claims.c.body["family"].astext.label("family"),
            support.c.value["coverage_id"].astext.label("coverage_id"),
            pin.c.task_id,
            pin.c.product_key,
            publication.c.build_id,
        )
        .select_from(
            claims.join(support, true())
            .outerjoin(
                input_,
                and_(
                    input_.c.product_id == build,
                    input_.c.revision_id == build,
                    input_.c.family == "input",
                    input_.c.local_id == support.c.value["input_index"].astext,
                ),
            )
            .outerjoin(
                pin,
                and_(
                    pin.c.task_id == cast(input_.c.body["task_id"].astext, pin.c.task_id.type),
                    pin.c.product_key == input_.c.body["product_key"].astext,
                    pin.c.content_digest == input_.c.body["content_digest"].astext,
                ),
            )
            .outerjoin(
                publication,
                and_(
                    publication.c.task_id == pin.c.task_id,
                    publication.c.product_key == pin.c.product_key,
                    publication.c.logical_digest == pin.c.content_digest,
                ),
            )
        )
        .cte("coverage_support_edges")
        .prefix_with("MATERIALIZED", dialect="postgresql")
    )
    resolved = union_all(
        select(
            edges.c.claim_id,
            edges.c.scope,
            edges.c.family,
            recorded.c.local_id.label("coverage_id"),
            recorded.c.body,
        )
        .select_from(
            edges.outerjoin(
                recorded,
                and_(
                    recorded.c.product_id == edges.c.build_id,
                    recorded.c.revision_id == edges.c.build_id,
                    recorded.c.family == "coverage",
                    recorded.c.local_id == edges.c.coverage_id,
                ),
            )
        )
        .where(edges.c.build_id.is_not(None)),
        select(
            edges.c.claim_id, edges.c.scope, edges.c.family, retained.c.coverage_id, retained.c.body
        )
        .select_from(
            edges.outerjoin(
                retained,
                and_(
                    retained.c.task_id == edges.c.task_id,
                    retained.c.product_key == edges.c.product_key,
                    retained.c.coverage_id == edges.c.coverage_id,
                ),
            )
        )
        .where(edges.c.build_id.is_(None)),
    ).cte("resolved_coverage_supports")
    compatible = and_(
        resolved.c.coverage_id.is_not(None),
        resolved.c.scope.is_not_distinct_from(resolved.c.body["scope"].astext),
        resolved.c.family.is_not_distinct_from(resolved.c.body["family"].astext),
    )
    summary = (
        select(
            resolved.c.claim_id,
            func.bool_or(~compatible).label("invalid_support"),
            func.bool_or(and_(compatible, resolved.c.body["outcome"].astext == "complete")).label(
                "complete_support"
            ),
        )
        .group_by(resolved.c.claim_id)
        .cte("coverage_support_summary")
    )
    invalid = (
        select(literal(1))
        .select_from(claims.outerjoin(summary, summary.c.claim_id == claims.c.claim_id))
        .where(
            or_(
                func.coalesce(summary.c.invalid_support, false()),
                and_(
                    claims.c.product_kind == "integrated",
                    claims.c.body["outcome"].astext == "complete",
                    ~func.coalesce(summary.c.complete_support, false()),
                ),
            )
        )
    )
    return invalid


def _published_pin_parameters(model):
    published = model.tables["ops.pdf_published_revision"]
    return tuple(
        Parameter(name, column_type(published.c[field]))
        for name, field in (
            ("p_task", "task_id"),
            ("p_key", "product_key"),
            ("p_digest", "logical_digest"),
        )
    )


def _published_pin_program(model, name, return_name, statement):
    returns = pg_type("ops", return_name)
    returns.setof = True
    source = "target-current:PDF publication"
    return ProgramDeclaration(
        NativeRoutine(
            "ops",
            name,
            parameters=_published_pin_parameters(model),
            returns=returns,
            body=statement(target_metadata=model),
            security_definer=True,
            search_path=("pg_catalog", "pg_temp"),
            volatility="stable",
            sql_standard=True,
        ),
        source + ":sql-standard",
        role_name("publisher"),
        NativeProgramAccess(purposes=("write", "read", "evaluate")),
    )


def published_pin_programs(model):
    from .native_sql_body import published_revision_statement, published_validation_statement

    return (
        _published_pin_program(
            model,
            "read_pdf_published_revision",
            "pdf_published_revision",
            published_revision_statement,
        ),
        _published_pin_program(
            model,
            "read_pdf_published_validation",
            "pdf_build_validation",
            published_validation_statement,
        ),
    )


def published_view_programs(model, domain):
    """Expose model-owned record fields and the captured PDF schema dependency."""
    published = model.tables["ops.pdf_published_revision"]
    companion = model.tables["kb.pdf_record_companion"]
    validation = model.tables["ops.pdf_build_validation"]
    contract_input = model.tables["sem.input"].alias("contract_input")
    from corpus_structure.schema.physical import compile_physical

    # Read shapes are a separate LinkML authority, never stored-table metadata.
    selected = compile_physical(
        {
            **model.info["physical_sources"],
            "read-projections.yaml": domain.source("logical/read_projections").content,
        },
        root="read-projections.yaml",
        target="semantic-read",
        linkml_types=model.info["physical_linkml_types"],
    ).tables["ops.pdf_selected_product"]
    from .native_program_registry import RelationProgramDeclaration

    programs = []

    def view(name, query, *, admitter=False):
        projection = (
            prepare_sql(
                str(query.compile(dialect=dialect(), compile_kwargs={"literal_binds": True})),
                source="published PDF view " + name,
            )
            .statements[0]
            .stmt
        )
        if not isinstance(projection, ast.SelectStmt):
            raise ValueError("published PDF view requires a structured SELECT")
        roles = (
            role_name("writer"),
            role_name("reader"),
            role_name("evaluator"),
            *((role_name("admitter"),) if admitter else ()),
        )
        programs.append(
            RelationProgramDeclaration(
                ast.ViewStmt(
                    view=ast.RangeVar(schemaname="ops", relname=name, inh=True),
                    query=projection,
                    replace=True,
                    withCheckOption=enums.ViewCheckOption.NO_CHECK_OPTION,
                ),
                "target-current:PDF views",
                role_name("publisher"),
                tuple((role, "SELECT", False) for role in roles),
            )
        )

    for family, name in (("access", "pdf_published_item"), ("region", "pdf_published_region")):
        records = model.tables["kb.pdf_record_" + family]
        view(
            name,
            select(
                published.c.task_id,
                published.c.product_key,
                *(
                    field
                    for field in records.columns
                    if field.key not in ("product_id", "revision_id")
                ),
            ).select_from(records.join(published, records.c.product_id == published.c.build_id)),
        )

    health = (
        select(
            companion.c.body.op("-", return_type=JSONB())(
                array(
                    ["source_scope", "page_start", "page_end"],
                    type_=Text(),
                )
            )
        )
        .where(
            companion.c.product_id == published.c.build_id,
            companion.c.revision_id == published.c.build_id,
            companion.c.family == "health",
            companion.c.body.has_key("source_scope"),
        )
        .order_by(companion.c.ordinal, companion.c.local_id)
        .limit(1)
        .correlate(published)
        .scalar_subquery()
    )
    view(
        "pdf_selected_product",
        select(
            published.c.task_id,
            published.c.product_key,
            published.c.logical_digest.label("content_digest"),
            published.c.release_id,
            contract_input.c.content_digest.label("contract_digest"),
            published.c.schema_digest,
            published.c.recipe_digest,
            cast(null(), selected.c.parent_task_id.type).label("parent_task_id"),
            cast(null(), selected.c.parent_product_key.type).label("parent_product_key"),
            cast(null(), selected.c.parent_digest.type).label("parent_digest"),
            cast(null(), selected.c.native_json.type).label("native_json"),
            health.label("health"),
            cast(null(), selected.c.payload.type).label("payload"),
        ).select_from(
            published.join(validation, validation.c.build_id == published.c.build_id).join(
                contract_input,
                (contract_input.c.release_id == published.c.release_id)
                & (contract_input.c.input_kind == "dependency")
                & (contract_input.c.input_name == domain.source("schema/pdf_products").name),
            )
        ),
        admitter=True,
    )

    value = func.ops.pdf_companion_body(
        companion.c.product_id,
        companion.c.revision_id,
        companion.c.family,
        companion.c.local_id,
        companion.c.body,
        type_=JSONB(),
    )["value"]
    coverage = (
        select(published.c.task_id, published.c.product_key, value.label("value"))
        .select_from(companion.join(published, published.c.build_id == companion.c.product_id))
        .where(
            companion.c.family == "native_metadata",
            companion.c.body["kind"].astext == "recognition_coverage",
        )
        .cte("coverage_")
        .prefix_with("MATERIALIZED", dialect="postgresql")
    )
    view(
        "pdf_published_coverage",
        select(
            coverage.c.task_id,
            coverage.c.product_key,
            *(
                coverage.c.value[field].astext.label(field)
                for field in (
                    "section_pointer",
                    "membership",
                    "universe",
                    "outcome",
                    "policy",
                )
            ),
        ),
    )
    return tuple(programs)


def _publication_stages():
    return {
        **STAGE_FAMILIES,
        "companion": "ops.pdf_stage_companion",
        "endpoint": "ops.pdf_stage_endpoint",
        "companion_field": "ops.pdf_stage_companion_field",
        "access": "ops.pdf_stage_access",
        "region": "ops.pdf_stage_region",
    }


def _prepare_binding(pdf_domain):
    from .pdf_domain import pdf_call_bindings

    (binding,) = (
        binding
        for action, binding in pdf_call_bindings(pdf_domain)
        if action == "prepare_pdf_build" and binding.id == "prepare_pdf_build"
    )
    return binding


def publication_control_programs(model, domain):
    """Own the build transition and publication routines and their access."""
    stages = _publication_stages()
    return (
        *pdf_freeze_native_programs(model, stages, pdf_domain=domain),
        _prepare_pdf_build_program(model, stages, _prepare_binding(domain)),
        *published_pin_programs(model),
        pdf_inventory_native_program(model),
        *pdf_validation_and_seal_native_programs(model, pdf_domain=domain),
        *pdf_publication_control_programs(model),
    )


def publication_native_programs(model, domain):
    """Collect publication routines at their typed producer boundaries."""
    from .pdf_certification_native import pdf_certification_native_programs
    from .pdf_companion_read_native import (
        pdf_companion_field_read_programs,
        pdf_native_record_shape_program,
    )
    from .pdf_publication_read_native import (
        pdf_publication_projection_program,
        pdf_record_scope_health_program,
        pdf_reference_bytes_equal_program,
    )
    from .pdf_record_context_native import (
        pdf_record_context_page_programs,
        pdf_record_context_programs,
    )
    from .pdf_record_pages_native import pdf_record_page_programs
    from .pdf_record_reader_native import (
        pdf_companion_export_programs,
        pdf_native_export_programs,
        pdf_record_reader_programs,
    )
    from .pdf_validation_read_native import pdf_validation_program_declarations

    return (
        pdf_native_record_shape_program(
            domain.source("implementation/pdf/docling-validation.schema.json").content
        ),
        *pdf_companion_field_read_programs(model),
        *publication_control_programs(model, domain),
        pdf_reference_bytes_equal_program(model),
        *pdf_record_reader_programs(target_metadata=model),
        *pdf_record_context_page_programs(model),
        *pdf_native_export_programs(target_metadata=model),
        *pdf_companion_export_programs(target_metadata=model),
        *pdf_record_page_programs(model, frozen=True),
        *pdf_validation_program_declarations(model, pdf_domain=domain).values(),
        *pdf_record_context_programs(model),
        *published_view_programs(model, domain),
        pdf_record_scope_health_program(model),
        pdf_publication_projection_program(model),
        *pdf_certification_native_programs(target_metadata=model),
    )


def pdf_freeze_native_programs(model, stages=None, *, pdf_domain=None):
    """Compile exact frozen inventory custody with hashing outside the owner lock."""
    from sqlalchemy import (
        BigInteger,
        Boolean,
        Text,
        any_,
        cast,
        column,
        exists,
        literal,
        not_,
        or_,
        tuple_,
        update,
    )
    from sqlalchemy.dialects.postgresql import BYTEA, JSONB, array

    from .native_program import (
        Assign,
        ForQuery,
        If,
        Local,
        Parameter,
        Perform,
        Raise,
        Return,
        SelectInto,
        Sql,
        Statement,
        column_type,
        pg_type,
    )

    stages = (
        {
            **STAGE_FAMILIES,
            "companion": "ops.pdf_stage_companion",
            "endpoint": "ops.pdf_stage_endpoint",
            "companion_field": "ops.pdf_stage_companion_field",
            "access": "ops.pdf_stage_access",
            "region": "ops.pdf_stage_region",
        }
        if stages is None
        else stages
    )
    inventory = {
        **stages,
        "spool_producer": "ops.pdf_spool_producer",
        "spool_contributor": "ops.pdf_spool_contributor",
        "producer_certification": "ops.pdf_producer_certification",
    }
    build = model.tables["ops.pdf_stage_build"]
    task = model.tables["ops.task"]
    request = model.tables["ops.data_request"]
    document = model.tables["kb.document"]
    sources = model.tables["ops.source_build"]
    recipes = model.tables["ops.pdf_stage_recipe"]
    artifacts = model.tables["kb.source_artifact"]
    frozen = model.tables["ops.pdf_frozen_build"]
    certified = model.tables["ops.pdf_producer_certification"]
    streams = model.tables["ops.pdf_stage_artifact_stream"]
    header = model.tables["ops.pdf_stage_document"]
    levels = _projection_write_levels(model, pdf_domain)
    fence = tuple(
        Parameter(name, column_type(field))
        for name, field in (
            ("p_build", build.c.build_id),
            ("p_task", build.c.task_id),
            ("p_attempt", build.c.attempt),
            ("p_holder", build.c.holder),
        )
    )
    p_build, p_task, p_attempt, p_holder = (
        core_variable(name, field.type)
        for name, field in (
            ("p_build", build.c.build_id),
            ("p_task", build.c.task_id),
            ("p_attempt", build.c.attempt),
            ("p_holder", build.c.holder),
        )
    )

    def row(name, relation, field):
        return core_variable(name, relation.c[field].type, field)

    owner_fields = {
        "project_id": request.c.project_id,
        "release_id": task.c.release_id,
        "request_id": request.c.id,
        "generation": task.c.data_generation,
        "document_id": document.c.id,
        "source_digest": document.c.content_hash,
    }

    def owner(field):
        return core_variable("owner", owner_fields[field].type, field)

    def require_owner_query(name):
        values = (
            func.ops.pdf_task_context(p_task)
            if name == "inspect"
            else func.ops.require_pdf_stage_owner(p_task, p_attempt, p_holder)
        )
        return SelectInto(
            select(
                values.table_valued(
                    *(column(field, source.type) for field, source in owner_fields.items())
                )
            ),
            ("owner",),
            True,
        )

    p_recipe = core_variable("p_recipe", BYTEA())
    recipe_digest = core_variable("digest_", Text())
    out = [
        _publication_control_routine(
            "bind_pdf_stage_recipe",
            (*fence[1:], Parameter("p_recipe", column_type(artifacts.c.content))),
            pg_type("text"),
            (
                require_owner_query("lock"),
                SelectInto(
                    select(sources).where(
                        sources.c.task_id == p_task, sources.c.release_id == owner("release_id")
                    ),
                    ("root_",),
                    True,
                ),
                Perform(
                    func.ops.require_pdf_operation(owner("release_id"), "retain_pdf_stage_recipe")
                ),
                Perform(cast(func.convert_from(p_recipe, "UTF8"), JSONB())),
                If(
                    or_(p_recipe.is_(None), func.octet_length(p_recipe) == 0),
                    (Raise("empty stage recipe", "P0001"),),
                ),
                Assign("digest_", func.encode(func.sha256(p_recipe), "hex")),
                Sql(
                    insert(artifacts)
                    .values(
                        {artifacts.c.artifact_digest: recipe_digest, artifacts.c.content: p_recipe}
                    )
                    .on_conflict_do_nothing()
                ),
                If(
                    ~exists(
                        select(1)
                        .select_from(artifacts)
                        .where(
                            artifacts.c.artifact_digest == recipe_digest,
                            artifacts.c.content == p_recipe,
                        )
                    ),
                    (Raise("stage recipe custody conflict", "P0001"),),
                ),
                Sql(
                    insert(recipes)
                    .values(
                        {
                            recipes.c.task_id: p_task,
                            recipes.c.source_digest: row("root_", sources, "artifact_digest"),
                            recipes.c.root_recipe_digest: row("root_", sources, "recipe_digest"),
                            recipes.c.stage_recipe_digest: recipe_digest,
                            recipes.c.release_id: owner("release_id"),
                        }
                    )
                    .on_conflict_do_nothing()
                ),
                Return(recipe_digest),
            ),
            (
                Local("owner", pg_type("record")),
                Local("root_", sources),
                Local("digest_", pg_type("text")),
            ),
        )
    ]

    p_frozen = core_variable("p_frozen", frozen.c.frozen_digest.type)
    out.append(
        _publication_control_routine(
            "require_pdf_frozen",
            (*fence, Parameter("p_frozen", column_type(frozen.c.frozen_digest))),
            pg_type(build.schema, build.name),
            (
                require_owner_query("inspect"),
                If(
                    not_(func.ops.pdf_stage_owner_current(p_task, p_attempt, p_holder)),
                    (Raise("stale frozen PDF owner", "P0004"),),
                ),
                SelectInto(
                    select(build).where(build.c.build_id == p_build, build.c.task_id == p_task),
                    ("b",),
                    True,
                ),
                If(
                    or_(
                        row("b", build, "release_id").is_distinct_from(owner("release_id")),
                        row("b", build, "state").not_in(("frozen", "published")),
                        row("b", build, "attempt").is_distinct_from(p_attempt),
                        row("b", build, "holder").is_distinct_from(p_holder),
                        ~exists(
                            select(1)
                            .select_from(frozen)
                            .where(frozen.c.build_id == p_build, frozen.c.frozen_digest == p_frozen)
                        ),
                    ),
                    (Raise("PDF frozen owner/inventory differs", "23514"),),
                ),
                Return(core_variable("b", JSONB())),
            ),
            (Local("b", build), Local("owner", pg_type("record"))),
            writer=False,
        )
    )

    p_kind = core_variable("p_kind", frozen.c.kind.type)
    state, payload = core_variable("state_", BYTEA()), core_variable("payload", BYTEA())
    count, total, family_count = (
        core_variable(name, BigInteger()) for name in ("count_", "total_", "family_count_")
    )
    inventory_value = core_variable("inventory_", JSONB())
    body = core_variable("body_", JSONB())
    digest = core_variable("f", frozen.c.frozen_digest.type)
    build_query = select(build).where(build.c.build_id == p_build, build.c.task_id == p_task)
    owner_changed = or_(
        row("b", build, "attempt").is_distinct_from(p_attempt),
        row("b", build, "holder").is_distinct_from(p_holder),
        row("b", build, "state") == "abandoned",
    )
    frozen_kind = select(frozen.c.kind).where(frozen.c.build_id == p_build).scalar_subquery()
    frozen_digest = (
        select(frozen.c.frozen_digest).where(frozen.c.build_id == p_build).scalar_subquery()
    )
    ready = ~exists(
        select(1)
        .select_from(streams)
        .where(
            streams.c.product_id == p_build,
            streams.c.revision_id == p_build,
            not_(
                func.ops.pdf_shared_stream_ready(
                    p_build, streams.c.encoding_profile, streams.c.byte_length, streams.c.byte_root
                )
            ),
        )
    )
    statements: list[Statement] = [
        If(
            not_(
                func.current_setting("transaction_isolation") == any_(array(levels, type_=Text()))
            ),
            (Raise("PDF freeze requires " + ", ".join(levels).upper(), "25000"),),
        ),
        require_owner_query("inspect"),
        If(
            not_(func.ops.pdf_stage_owner_current(p_task, p_attempt, p_holder)),
            (Raise("stale private PDF build owner", "P0004"),),
        ),
        SelectInto(build_query, ("b",), True),
        If(owner_changed, (Raise("PDF freeze owner differs", "23514"),)),
        SelectInto(select(frozen.c.frozen_digest).where(frozen.c.build_id == p_build), ("f",)),
        If(
            core_variable("found", Boolean()),
            (
                Perform(func.ops.require_pdf_stage_owner(p_task, p_attempt, p_holder)),
                SelectInto(build_query.with_for_update(), ("b",), True),
                If(owner_changed, (Raise("PDF freeze owner differs", "23514"),)),
                If(
                    p_kind.is_distinct_from(frozen_kind),
                    (Raise("frozen publication kind differs", "P0001"),),
                ),
                Return(digest),
            ),
        ),
        Perform(func.ops.require_pdf_operation(row("b", build, "release_id"), "freeze_pdf_build")),
        If(
            not_(ready),
            (Raise("PDF freeze requires verified project-scoped stream bytes", "23514"),),
        ),
    ]
    for family, name in sorted(inventory.items()):
        relation = model.tables[name]
        alias = relation.alias("t")
        owner_column = (
            "build_id"
            if family.startswith("spool_") or family == "producer_certification"
            else "product_id"
        )
        statements.extend(
            (
                Assign("family_count_", literal(0)),
                ForQuery(
                    ("body_",),
                    select(func.to_jsonb(alias.table_valued()))
                    .where(alias.c[owner_column] == p_build)
                    .order_by(*(alias.c[field.name] for field in relation.primary_key)),
                    (
                        Assign("payload", func.convert_to(cast(body, Text()), "UTF8")),
                        Assign(
                            "state_",
                            func.ops.pdf_identity_fold_step(
                                state,
                                count,
                                func.convert_to(family + ":", "UTF8").op("||")(
                                    func.sha256(payload)
                                ),
                            ),
                        ),
                        Assign("count_", count + 1),
                        Assign("total_", total + func.octet_length(payload)),
                        Assign("family_count_", family_count + 1),
                    ),
                ),
                Assign(
                    "inventory_",
                    inventory_value.op("||")(func.jsonb_build_object(family, family_count)),
                ),
            )
        )
    statements.extend(
        (
            If(
                ~exists(
                    select(1)
                    .select_from(certified)
                    .where(
                        certified.c.build_id == p_build,
                        certified.c.kind == p_kind,
                        certified.c.lowering_identity
                        == func.ops.pdf_lowering_identity(row("b", build, "release_id")),
                        tuple_(
                            certified.c.source_digest,
                            certified.c.recipe_digest,
                            certified.c.schema_digest,
                        )
                        == tuple_(
                            row("b", build, "source_digest"),
                            row("b", build, "recipe_digest"),
                            row("b", build, "schema_digest"),
                        ),
                    )
                ),
                (Raise("PDF freeze requires exact producer certification", "23514"),),
            ),
            If(
                ~exists(select(1).select_from(header).where(header.c.product_id == p_build)),
                (Raise("PDF freeze has no native document header", "23514"),),
            ),
            Assign("f", func.encode(func.ops.pdf_identity_fold_finish(state, count, total), "hex")),
            require_owner_query("lock"),
            SelectInto(build_query.with_for_update(), ("b",), True),
            If(
                or_(
                    row("b", build, "release_id").is_distinct_from(owner("release_id")),
                    owner_changed,
                ),
                (Raise("PDF freeze owner differs", "23514"),),
            ),
            If(
                exists(select(1).select_from(frozen).where(frozen.c.build_id == p_build)),
                (
                    If(
                        p_kind.is_distinct_from(frozen_kind),
                        (Raise("frozen publication kind differs", "P0001"),),
                    ),
                    Return(frozen_digest),
                ),
            ),
            If(
                row("b", build, "state") != "open",
                (Raise("PDF freeze build is not open", "23514"),),
            ),
            If(
                not_(ready),
                (Raise("PDF freeze requires verified project-scoped stream bytes", "23514"),),
            ),
        )
    )
    for family, name in sorted(inventory.items()):
        relation = model.tables[name]
        owner_column = (
            "build_id"
            if family.startswith("spool_") or family == "producer_certification"
            else "product_id"
        )
        statements.extend(
            (
                SelectInto(
                    select(func.count())
                    .select_from(relation)
                    .where(relation.c[owner_column] == p_build),
                    ("family_count_",),
                ),
                If(
                    family_count.is_distinct_from(
                        cast(inventory_value[family].astext, BigInteger())
                    ),
                    (
                        Raise(
                            "PDF freeze inventory changed; retry from the current private build",
                            "40001",
                        ),
                    ),
                ),
            )
        )
    statements.extend(
        (
            Sql(
                insert(frozen).values(
                    {
                        frozen.c.build_id: p_build,
                        frozen.c.frozen_digest: digest,
                        frozen.c.kind: p_kind,
                    }
                )
            ),
            Sql(update(build).values({build.c.state: "frozen"}).where(build.c.build_id == p_build)),
            Return(digest),
        )
    )
    out.append(
        _publication_control_routine(
            "freeze_pdf_build",
            (*fence, Parameter("p_kind", column_type(frozen.c.kind))),
            pg_type("text"),
            statements,
            (
                Local("b", build),
                Local("owner", pg_type("record")),
                Local("f", pg_type("text")),
                Local(
                    "state_",
                    pg_type("bytea"),
                    func.ops.pdf_identity_fold_start("pdf-frozen-inventory-v1"),
                ),
                Local("body_", pg_type("jsonb")),
                Local("payload", pg_type("bytea")),
                Local("count_", pg_type("bigint"), literal(0)),
                Local("total_", pg_type("bigint"), literal(0)),
                Local("family_count_", pg_type("bigint")),
                Local("inventory_", pg_type("jsonb"), cast(literal("{}"), JSONB())),
            ),
        )
    )
    return tuple(out)


def _publication_program(routine, *, writer=True, source="target-current:PDF publication"):
    return ProgramDeclaration(
        routine,
        source,
        role_name("publisher"),
        NativeProgramAccess(purposes=("write",)) if writer else INTERNAL_PROGRAM,
    )


def _publication_control_routine(
    name, parameters, returns, statements, locals_, *, writer=True, security_definer=True
):
    from .native_program import Block

    return _publication_program(
        NativeRoutine(
            "ops",
            name,
            parameters=parameters,
            returns=returns,
            body=Block(tuple(statements), tuple(locals_)),
            security_definer=security_definer,
            search_path=("pg_catalog", "pg_temp"),
        ),
        writer=writer,
    )


def _publication_program_sql(program):
    return (
        native_sql_script(
            (
                program.routine.render(),
                native_privilege_sql(program.identity, "PUBLIC", grant=False),
                *(
                    native_privilege_sql(
                        program.identity, role, privilege, grant_option=grant_option
                    )
                    for role, privilege, grant_option in program.access.grants(program.owner)
                ),
            )
        )
        + "\n"
    )


def pdf_freeze_native_sql(model, stages=None, *, pdf_domain=None):
    return "\n".join(
        _publication_program_sql(item)
        for item in pdf_freeze_native_programs(model, stages, pdf_domain=pdf_domain)
    )


def pdf_publication_controls_sql(model):
    return "\n".join(
        _publication_program_sql(item) for item in pdf_publication_control_programs(model)
    )


def pdf_validation_and_seal_native_sql(model, *, pdf_domain=None):
    return "\n".join(
        _publication_program_sql(item)
        for item in pdf_validation_and_seal_native_programs(model, pdf_domain=pdf_domain)
    )


def pdf_inventory_native_sql(model):
    return _publication_program_sql(pdf_inventory_native_program(model))


def pdf_publication_control_programs(model):
    """Generate bounded projection admission and exact private build lookup controls."""
    from pglast import ast
    from sqlalchemy import BigInteger, Text, cast, column, exists, or_
    from sqlalchemy.dialects.postgresql import JSONB

    from .native_program import (
        Assign,
        ForQuery,
        If,
        Local,
        Parameter,
        Perform,
        Raise,
        Return,
        ReturnQuery,
        SelectInto,
        Sql,
        call,
        column_type,
        pg_type,
        variable,
    )

    build = model.tables["ops.pdf_stage_build"]
    task = model.tables["ops.task"]
    frozen = model.tables["ops.pdf_frozen_build"]
    validation = model.tables["ops.pdf_build_validation"]
    published = model.tables["ops.pdf_published_revision"]
    access = model.tables["ops.pdf_stage_access"]
    region = model.tables["ops.pdf_stage_region"]
    p_build, p_task, p_attempt, p_holder = (
        core_variable(name, field.type)
        for name, field in (
            ("p_build", build.c.build_id),
            ("p_task", build.c.task_id),
            ("p_attempt", build.c.attempt),
            ("p_holder", build.c.holder),
        )
    )
    fence = tuple(
        Parameter(name, column_type(field))
        for name, field in (
            ("p_build", build.c.build_id),
            ("p_task", build.c.task_id),
            ("p_attempt", build.c.attempt),
            ("p_holder", build.c.holder),
        )
    )
    owner_rows = func.ops.require_pdf_stage_owner(p_task, p_attempt, p_holder).table_valued(
        column("release_id", task.c.release_id.type)
    )
    require_owner = Perform(func.ops.require_pdf_stage_owner(p_task, p_attempt, p_holder))
    require_build = Assign("b", func.ops.require_pdf_build(p_build, p_task, p_attempt, p_holder))
    p_frozen = core_variable("p_frozen", frozen.c.frozen_digest.type)
    body, row, family = (
        core_variable(name, type_)
        for name, type_ in (
            ("body_", JSONB()),
            ("row_", JSONB()),
            ("family_", Text()),
        )
    )
    payload = core_variable("p_rows", JSONB())
    incoming = func.jsonb_array_elements(payload).table_valued(column("value", JSONB()))

    def projection_statements(relation, local, family_name):
        alias = relation.alias("r")
        row_equal = (
            func.to_jsonb(alias.table_valued(), type_=JSONB()) - "product_id" - "revision_id"
        )
        conditions = [
            alias.c.product_id == p_build,
            alias.c.revision_id == p_build,
            alias.c.pointer == body["pointer"].astext,
            row_equal == body,
        ]
        if family_name == "region":
            conditions.append(
                alias.c.region_index == cast(body["region_index"].astext, BigInteger())
            )
        return (
            Assign(
                local,
                call(
                    "pg_catalog",
                    "jsonb_populate_record",
                    ast.TypeCast(
                        arg=ast.A_Const(isnull=True),
                        typeName=pg_type(relation.schema, relation.name),
                    ),
                    variable("owned_"),
                ),
            ),
            Sql(
                insert(relation)
                .values(
                    {field: core_variable(local, field.type, field.name) for field in relation.c}
                )
                .on_conflict_do_nothing()
            ),
            If(
                ~exists(select(1).select_from(alias).where(*conditions)),
                (Raise("changed " + family_name + " projection", "23514"),),
            ),
        )

    out = [
        _publication_control_routine(
            "stage_pdf_access_batch",
            (*fence, Parameter("p_rows", pg_type("jsonb"))),
            pg_type("void"),
            (
                require_build,
                Perform(
                    func.ops.require_pdf_operation(
                        core_variable("b", build.c.release_id.type, "release_id"),
                        "stage_pdf_producer",
                    )
                ),
                If(
                    or_(
                        func.jsonb_typeof(payload).is_distinct_from("array"),
                        func.jsonb_array_length(payload) > 128,
                        func.octet_length(cast(payload, Text())) > 16777216,
                    ),
                    (Raise("access projection batch exceeds profile", "P0001"),),
                ),
                ForQuery(
                    ("row_",),
                    select(incoming.c.value),
                    (
                        Assign("family_", row["family"].astext),
                        Assign("body_", row["body"]),
                        Assign(
                            "owned_",
                            body.op("||")(
                                func.jsonb_build_object(
                                    "product_id", p_build, "revision_id", p_build
                                )
                            ),
                        ),
                        If(
                            family == "access",
                            projection_statements(access, "access_", "access"),
                            (
                                If(
                                    family == "region",
                                    projection_statements(region, "region_", "region"),
                                    (Raise("invalid projection family", "P0001"),),
                                ),
                            ),
                        ),
                    ),
                ),
            ),
            (
                Local("b", build),
                Local("row_", pg_type("jsonb")),
                Local("body_", pg_type("jsonb")),
                Local("family_", pg_type("text")),
                Local("owned_", pg_type("jsonb")),
                Local("access_", access),
                Local("region_", region),
            ),
        )
    ]

    build_type = pg_type(build.schema, build.name)
    build_type.setof = True
    out.append(
        _publication_control_routine(
            "lookup_pdf_build",
            (*fence[1:], Parameter("p_key", column_type(build.c.replay_key))),
            build_type,
            (
                SelectInto(select(owner_rows), ("owner",), True),
                Perform(
                    func.ops.require_pdf_operation(
                        core_variable("owner", task.c.release_id.type, "release_id"),
                        "inspect_pdf_build",
                    )
                ),
                ReturnQuery(
                    select(build).where(
                        build.c.task_id == p_task,
                        build.c.replay_key == core_variable("p_key", build.c.replay_key.type),
                        build.c.release_id
                        == core_variable("owner", task.c.release_id.type, "release_id"),
                    )
                ),
            ),
            (Local("owner", pg_type("record")),),
        )
    )
    for name, field in (
        ("lookup_pdf_frozen_digest", frozen.c.frozen_digest),
        ("lookup_pdf_frozen_kind", frozen.c.kind),
    ):
        out.append(
            _publication_control_routine(
                name,
                fence,
                column_type(field),
                (
                    require_owner,
                    If(
                        ~exists(
                            select(1)
                            .select_from(build)
                            .where(build.c.build_id == p_build, build.c.task_id == p_task)
                        ),
                        (Raise("build outside task", "P0001"),),
                    ),
                    SelectInto(select(field).where(frozen.c.build_id == p_build), ("value_",)),
                    Return(core_variable("value_", field.type)),
                ),
                (Local("value_", column_type(field)),),
            )
        )
    contract = core_variable("native_contract_", validation.c.native_contract_digest.type)
    validation_type = pg_type(validation.schema, validation.name)
    validation_type.setof = True
    out.append(
        _publication_control_routine(
            "lookup_pdf_validation",
            (*fence, Parameter("p_frozen", column_type(frozen.c.frozen_digest))),
            validation_type,
            (
                Assign(
                    "b", func.ops.require_pdf_frozen(p_build, p_task, p_attempt, p_holder, p_frozen)
                ),
                Assign(
                    "native_contract_",
                    func.ops.pdf_validation_contract(
                        core_variable("b", build.c.release_id.type, "release_id")
                    ),
                ),
                If(
                    exists(
                        select(1)
                        .select_from(validation)
                        .where(
                            validation.c.build_id == p_build,
                            validation.c.frozen_digest == p_frozen,
                            validation.c.native_contract_digest.is_distinct_from(contract),
                        )
                    ),
                    (
                        Raise(
                            "PDF validation profile differs; rebuild from retained evidence in a fresh current storage build; do not alter stored pins",
                            "23514",
                        ),
                    ),
                ),
                ReturnQuery(
                    select(validation).where(
                        validation.c.build_id == p_build,
                        validation.c.frozen_digest == p_frozen,
                        validation.c.native_callbacks,
                        validation.c.native_contract_digest == contract,
                    )
                ),
            ),
            (
                Local("b", build),
                Local("native_contract_", column_type(validation.c.native_contract_digest)),
            ),
        )
    )
    published_type = pg_type(published.schema, published.name)
    published_type.setof = True
    out.append(
        _publication_control_routine(
            "lookup_pdf_published_build",
            fence,
            published_type,
            (
                require_owner,
                ReturnQuery(
                    select(published).where(
                        published.c.build_id == p_build, published.c.task_id == p_task
                    )
                ),
            ),
            (),
        )
    )
    return tuple(out)


def _projection_write_levels(model, pdf_domain):
    from .pdf_contracts import _context_from_domain, projection_write_levels, trusted_pdf_context

    context = (
        trusted_pdf_context() if pdf_domain is None else _context_from_domain(None, pdf_domain)
    )
    return projection_write_levels(context, model.info["physical_sources"]["pdf-staging.yaml"])


def pdf_validation_and_seal_native_programs(model, *, pdf_domain=None):
    """Generate qualified validation and atomic publication of immutable PDF pins."""
    from sqlalchemy import Boolean, Text, any_, cast, column, exists, literal, not_, or_, update
    from sqlalchemy.dialects.postgresql import array

    from .native_program import (
        Assign,
        If,
        Local,
        Parameter,
        Perform,
        PerformQuery,
        Raise,
        Return,
        ReturnQuery,
        SelectInto,
        Sql,
        column_type,
        pg_type,
    )

    build = model.tables["ops.pdf_stage_build"]
    frozen = model.tables["ops.pdf_frozen_build"]
    validation = model.tables["ops.pdf_build_validation"]
    published = model.tables["ops.pdf_published_revision"]
    checks = model.tables["ops.pdf_validation_check"]
    certification = model.tables["ops.pdf_producer_certification"]
    companion = model.tables["kb.pdf_record_companion"]
    product = model.tables["ops.pdf_product"]
    product_input = model.tables["ops.pdf_product_input"]
    product_artifact = model.tables["ops.pdf_product_artifact"]
    artifact = model.tables["kb.source_artifact"]
    request = model.tables["ops.data_request"]
    fence = tuple(
        Parameter(name, column_type(field))
        for name, field in (
            ("p_build", build.c.build_id),
            ("p_task", build.c.task_id),
            ("p_attempt", build.c.attempt),
            ("p_holder", build.c.holder),
            ("p_frozen", frozen.c.frozen_digest),
        )
    )
    p_build, p_task, p_attempt, p_holder, p_frozen = (
        core_variable(name, field.type)
        for name, field in (
            ("p_build", build.c.build_id),
            ("p_task", build.c.task_id),
            ("p_attempt", build.c.attempt),
            ("p_holder", build.c.holder),
            ("p_frozen", frozen.c.frozen_digest),
        )
    )

    def row(name, relation, field):
        return core_variable(name, relation.c[field].type, field)

    def qualification(field):
        source = qualification_sources[field]
        return core_variable("certification_", source.type, field)

    def local_result(name, relation):
        return select(*(core_variable(name, field.type, field.name) for field in relation.c))

    has_seal_check = exists(
        select(1)
        .select_from(checks)
        .where(checks.c.build_id == p_build, checks.c.check_name == "seal")
    )
    require_owner = Perform(func.ops.require_pdf_stage_owner(p_task, p_attempt, p_holder))
    lock_build = PerformQuery(
        select(literal(1))
        .select_from(build)
        .where(build.c.build_id == p_build)
        .with_for_update(key_share=True)
    )
    require_frozen = Assign(
        "b", func.ops.require_pdf_frozen(p_build, p_task, p_attempt, p_holder, p_frozen)
    )
    lookup = func.ops.lookup_pdf_validation(
        p_build, p_task, p_attempt, p_holder, p_frozen
    ).table_valued(*(column(field.name, field.type) for field in validation.c))
    qualified_fields = (
        ("lowering_identity", certification.c.lowering_identity),
        ("kind", certification.c.kind),
        ("logical_digest", certification.c.logical_digest),
        ("native_document_digest", certification.c.native_document_digest),
        ("oracle_receipt_id", validation.c.oracle_receipt_id),
        ("certification_basis", validation.c.certification_basis),
    )
    qualification_sources = dict(qualified_fields)
    qualified = func.ops.read_pdf_certification_requirement(
        p_build, p_task, p_attempt, p_holder, p_frozen
    ).table_valued(*(column(name, field.type) for name, field in qualified_fields))
    logical = core_variable("logical_", validation.c.logical_digest.type)
    contract = core_variable("contract_", validation.c.contract_digest.type)
    native_contract = func.ops.pdf_validation_contract(row("b", build, "release_id"))
    context = func.ops.pdf_task_context(row("b", build, "task_id")).table_valued(
        column("project_id", request.c.project_id.type)
    )
    levels = _projection_write_levels(model, pdf_domain)
    validation_type = pg_type(validation.schema, validation.name)
    validation_type.setof = True
    validate = _publication_control_routine(
        "validate_pdf_build",
        fence,
        validation_type,
        (
            If(
                not_(
                    func.current_setting("transaction_isolation")
                    == any_(array(levels, type_=Text()))
                ),
                (Raise("PDF projection admission requires " + ", ".join(levels).upper(), "25000"),),
            ),
            If(has_seal_check, (require_owner,)),
            lock_build,
            require_frozen,
            Perform(
                func.ops.require_pdf_operation(row("b", build, "release_id"), "validate_pdf_build")
            ),
            SelectInto(select(lookup), ("prior_validation",)),
            If(
                core_variable("found", Boolean()),
                (ReturnQuery(local_result("prior_validation", validation)), Return()),
            ),
            SelectInto(select(qualified), ("certification_",), True),
            If(
                qualification("oracle_receipt_id").is_(None),
                (Raise("PDF lowering has no passed round-trip oracle", "23514"),),
            ),
            If(
                has_seal_check,
                (
                    SelectInto(
                        select(
                            func.max(checks.c.result_digest).filter(
                                checks.c.check_name == "identity"
                            ),
                            func.max(checks.c.result_digest).filter(
                                checks.c.check_name == "projection"
                            ),
                        )
                        .where(
                            checks.c.build_id == p_build,
                            checks.c.attempt == p_attempt,
                            checks.c.holder == p_holder,
                            checks.c.frozen_digest == p_frozen,
                            checks.c.contract_digest == native_contract,
                        )
                        .having(func.count() == 5),
                        ("logical_", "contract_"),
                    ),
                    If(
                        or_(logical.is_(None), contract.is_(None)),
                        (Raise("incomplete frozen PDF validation checks", "23514"),),
                    ),
                ),
                (
                    Perform(
                        func.ops.pdf_check_build_inventory(
                            p_build,
                            row("b", build, "source_digest"),
                            select(context.c.project_id).scalar_subquery(),
                        )
                    ),
                    Perform(func.ops.pdf_check_access_correspondence(p_build)),
                    Assign("logical_", func.ops.pdf_record_logical_identity(p_build, p_build)),
                    Assign(
                        "contract_",
                        func.ops.pdf_projection_contract(p_build, row("b", build, "release_id")),
                    ),
                ),
            ),
            Perform(func.ops.require_pdf_frozen(p_build, p_task, p_attempt, p_holder, p_frozen)),
            If(
                func.ops.pdf_producer_stream_identity(
                    p_build, row("b", build, "schema_digest")
                ).is_distinct_from(
                    select(certification.c.stream_inventory_digest)
                    .where(certification.c.build_id == p_build)
                    .scalar_subquery()
                ),
                (Raise("stored PDF stream roots differ from producer attestation", "23514"),),
            ),
            If(
                logical.is_distinct_from(qualification("logical_digest")),
                (Raise("stored PDF identity differs from producer attestation", "23514"),),
            ),
            Sql(
                insert(validation)
                .values(
                    {
                        validation.c.build_id: p_build,
                        validation.c.frozen_digest: p_frozen,
                        validation.c.logical_digest: logical,
                        validation.c.contract_digest: contract,
                        validation.c.native_callbacks: True,
                        validation.c.native_contract_digest: native_contract,
                        validation.c.certification_basis: qualification("certification_basis"),
                        validation.c.lowering_identity: qualification("lowering_identity"),
                        validation.c.attested_logical_digest: qualification("logical_digest"),
                        validation.c.native_document_digest: qualification(
                            "native_document_digest"
                        ),
                        validation.c.oracle_receipt_id: qualification("oracle_receipt_id"),
                    }
                )
                .on_conflict_do_nothing()
            ),
            If(
                ~exists(
                    select(1)
                    .select_from(validation)
                    .where(
                        validation.c.build_id == p_build,
                        validation.c.frozen_digest == p_frozen,
                        validation.c.logical_digest == logical,
                        validation.c.contract_digest == contract,
                        validation.c.native_contract_digest == native_contract,
                        validation.c.native_callbacks,
                    )
                ),
                (Raise("PDF validation result differs for frozen premises", "23514"),),
            ),
            ReturnQuery(
                select(validation).where(
                    validation.c.build_id == p_build,
                    validation.c.frozen_digest == p_frozen,
                    validation.c.contract_digest == contract,
                )
            ),
        ),
        (
            Local("b", build),
            Local("logical_", column_type(validation.c.logical_digest)),
            Local("contract_", column_type(validation.c.contract_digest)),
            Local("certification_", pg_type("record")),
            Local("prior_validation", validation),
        ),
    )

    p_key = core_variable("p_key", published.c.product_key.type)
    kind = core_variable("kind_", frozen.c.kind.type)
    published_type = pg_type(published.schema, published.name)
    published_type.setof = True
    seal = _publication_control_routine(
        "seal_pdf_build",
        (*fence, Parameter("p_key", column_type(published.c.product_key))),
        published_type,
        (
            require_owner,
            lock_build,
            require_frozen,
            SelectInto(select(published).where(published.c.build_id == p_build), ("prior",)),
            If(
                core_variable("found", Boolean()),
                (
                    If(
                        row("prior", published, "product_key").is_distinct_from(p_key),
                        (Raise("published key replay differs", "P0001"),),
                    ),
                    ReturnQuery(local_result("prior", published)),
                    Return(),
                ),
            ),
            Perform(
                func.ops.require_pdf_operation(row("b", build, "release_id"), "seal_pdf_build")
            ),
            SelectInto(select(lookup), ("v",), True),
            If(or_(p_key.is_(None), p_key == ""), (Raise("empty PDF product key", "P0001"),)),
            SelectInto(select(frozen.c.kind).where(frozen.c.build_id == p_build), ("kind_",), True),
            If(
                (kind == "integrated")
                & or_(
                    ~exists(
                        select(1)
                        .select_from(companion)
                        .where(companion.c.product_id == p_build, companion.c.family == "input")
                    ),
                    ~exists(
                        select(1)
                        .select_from(companion)
                        .where(companion.c.product_id == p_build, companion.c.family == "coverage")
                    ),
                ),
                (Raise("integrated publication lacks input/coverage inventory", "23514"),),
            ),
            Sql(
                insert(product).values(
                    {
                        product.c.task_id: p_task,
                        product.c.product_key: p_key,
                        product.c.content_digest: row("v", validation, "logical_digest"),
                        product.c.kind: kind,
                        product.c.artifact_digest: row("b", build, "source_digest"),
                        product.c.release_id: row("b", build, "release_id"),
                        product.c.contract_digest: row("v", validation, "contract_digest"),
                    }
                )
            ),
            Sql(
                insert(product_input).from_select(
                    (
                        product_input.c.task_id,
                        product_input.c.product_key,
                        product_input.c.input_index,
                        product_input.c.role,
                        product_input.c.input_task_id,
                        product_input.c.input_product_key,
                        product_input.c.input_content_digest,
                    ),
                    select(
                        p_task,
                        p_key,
                        cast(companion.c.local_id, product_input.c.input_index.type),
                        companion.c.body["role"].astext,
                        cast(
                            companion.c.body["task_id"].astext, product_input.c.input_task_id.type
                        ),
                        companion.c.body["product_key"].astext,
                        companion.c.body["content_digest"].astext,
                    ).where(companion.c.product_id == p_build, companion.c.family == "input"),
                )
            ),
            Sql(
                insert(artifact)
                .from_select(
                    (artifact.c.artifact_digest, artifact.c.content),
                    select(
                        row("b", build, "schema_digest"),
                        func.ops.pdf_contract_input(
                            row("b", build, "release_id"),
                            "implementation/pdf/docling-validation.schema.json",
                        ),
                    ),
                )
                .on_conflict_do_nothing()
            ),
            Sql(
                insert(product_artifact).from_select(
                    (
                        product_artifact.c.task_id,
                        product_artifact.c.product_key,
                        product_artifact.c.artifact_digest,
                    ),
                    select(p_task, p_key, artifact.c.artifact_digest).where(
                        artifact.c.artifact_digest.in_(
                            (
                                row("b", build, "source_digest"),
                                row("b", build, "schema_digest"),
                                row("b", build, "recipe_digest"),
                            )
                        )
                    ),
                )
            ),
            SelectInto(
                insert(published)
                .values(
                    {
                        published.c.build_id: p_build,
                        published.c.task_id: p_task,
                        published.c.product_key: p_key,
                        published.c.logical_digest: row("v", validation, "logical_digest"),
                        published.c.release_id: row("b", build, "release_id"),
                        published.c.source_digest: row("b", build, "source_digest"),
                        published.c.schema_digest: row("b", build, "schema_digest"),
                        published.c.recipe_digest: row("b", build, "recipe_digest"),
                        published.c.frozen_digest: p_frozen,
                        published.c.kind: kind,
                    }
                )
                .returning(*published.c),
                ("prior",),
            ),
            Sql(
                update(build)
                .values({build.c.state: "published"})
                .where(build.c.build_id == p_build)
            ),
            ReturnQuery(local_result("prior", published)),
        ),
        (
            Local("b", build),
            Local("v", validation),
            Local("prior", published),
            Local("kind_", column_type(frozen.c.kind)),
        ),
    )
    return (validate, seal)


def pdf_inventory_native_program(model):
    """Compile native containment, normalized identity and exact companion custody."""
    from sqlalchemy import (
        BigInteger,
        Boolean,
        Text,
        and_,
        cast,
        column,
        exists,
        literal,
        not_,
        or_,
        true,
    )
    from sqlalchemy.dialects.postgresql import JSONB

    from .native_program import (
        If,
        Local,
        Parameter,
        Raise,
        SelectInto,
        Statement,
        column_type,
        pg_type,
    )
    from .pdf_payloads import FAMILY, PROFILE

    native = model.tables["kb.pdf_record_native"].alias("n")
    membership = model.tables["kb.pdf_record_membership"].alias("m")
    reference = model.tables["kb.pdf_record_reference"].alias("r")
    document = model.tables["ops.pdf_record_document"]
    access = model.tables["kb.pdf_record_access"]
    companion = model.tables["kb.pdf_record_companion"]
    endpoint = model.tables["kb.pdf_record_endpoint"]
    companion_field = model.tables["kb.pdf_record_companion_field"]
    stream = model.tables["ops.pdf_artifact_stream"]
    product = model.tables["ops.pdf_product"]
    published = model.tables["ops.pdf_published_revision"]
    legacy_occurrence = model.tables["kb.pdf_occurrence"]
    product_body = model.tables["ops.pdf_product_body"]
    p_build = core_variable("p_build", native.c.product_id.type)
    p_source = core_variable("p_source", model.tables["ops.pdf_stage_build"].c.source_digest.type)
    p_project = core_variable("p_project", model.tables["ops.data_request"].c.project_id.type)
    empty = cast(literal("[]"), JSONB())

    def scope(relation):
        return and_(relation.c.product_id == p_build, relation.c.revision_id == p_build)

    def fields(relation):
        return (
            func.jsonb_each(relation.c.structure_json["fields"])
            .table_valued(column("key", Text()), column("value", JSONB()))
            .lateral("fields")
        )

    def reject(query, message, state="23514"):
        return If(exists(query), (Raise(message, state),))

    f = fields(native)
    scalar_keys = (
        func.jsonb_object_keys(native.c.scalars_json)
        .table_valued(column("key", Text()))
        .render_derived()
    )
    statements: list[Statement] = [
        reject(
            select(1)
            .select_from(native)
            .where(
                scope(native),
                func.ops.pdf_native_record_shape(
                    native.c.native_type, native.c.scalars_json, native.c.structure_json["fields"]
                ).is_not(True),
            ),
            "native schema field/required/primitive constraint differs",
        ),
        reject(
            select(1)
            .select_from(native)
            .where(
                scope(native),
                or_(
                    func.jsonb_typeof(native.c.structure_json["fields"]).is_distinct_from("object"),
                    exists(
                        select(1)
                        .select_from(f)
                        .where(f.c.value["kind"].astext.not_in(("object", "array", "map", "parts")))
                    ),
                    exists(
                        select(1)
                        .select_from(scalar_keys)
                        .where(native.c.structure_json["fields"].has_key(scalar_keys.c.key))
                    ),
                ),
            ),
            "invalid native field decomposition",
        ),
        reject(
            select(1)
            .select_from(
                membership.outerjoin(
                    native, and_(scope(native), native.c.record_id == membership.c.parent_id)
                )
            )
            .where(
                scope(membership),
                or_(
                    native.c.record_id.is_(None),
                    native.c.structure_json["fields"][membership.c.field_name][
                        "kind"
                    ].astext.not_in(("array", "map")),
                ),
            ),
            "membership outside declared collection",
        ),
        reject(
            select(1)
            .select_from(native)
            .where(scope(native), native.c.scalars_json.has_key("self_ref"))
            .group_by(native.c.scalars_json["self_ref"].astext)
            .having(func.count() != 1),
            "native self-reference is not unique",
        ),
    ]
    ref_index = (
        select(
            reference.c.reference_id,
            reference.c.source_id,
            reference.c.native_pointer,
            reference.c.native_pointer_stream_id,
        )
        .where(scope(reference), reference.c.field_name == "$ref")
        .cte("ref_index")
        .prefix_with("MATERIALIZED", dialect="postgresql")
    )
    reference_spelling = case(
        (
            and_(
                ref_index.c.native_pointer_stream_id.is_(None),
                native.c.structure_json["fields"]["$ref"]["stream_id"].astext.is_(None),
            ),
            (
                ref_index.c.native_pointer.collate("C")
                == native.c.scalars_json["$ref"].astext.collate("C")
            ).is_not(True),
        ),
        else_=not_(
            func.ops.pdf_reference_bytes_equal(
                p_build,
                p_build,
                ref_index.c.native_pointer,
                ref_index.c.native_pointer_stream_id,
                native.c.scalars_json["$ref"].astext,
                native.c.structure_json["fields"]["$ref"]["stream_id"].astext,
            )
        ),
    )
    statements.append(
        reject(
            select(1)
            .select_from(native.outerjoin(ref_index, ref_index.c.source_id == native.c.record_id))
            .where(
                scope(native),
                native.c.native_type.in_(("RefItem", "FineRef")),
                or_(ref_index.c.reference_id.is_(None), reference_spelling),
            ),
            "native reference index does not correspond to supplied spelling",
        )
    )

    owner_edges = (
        union_all(
            select(
                native.c.record_id.label("parent_id"), f.c.value["target"].astext.label("child_id")
            )
            .select_from(native.join(f, true()))
            .where(scope(native), f.c.value["kind"].astext == "object"),
            select(membership.c.parent_id, membership.c.record_id).where(
                scope(membership), membership.c.value_kind == "record"
            ),
        )
        .cte("owner_edges")
        .prefix_with("MATERIALIZED", dialect="postgresql")
    )
    owner_counts = (
        select(owner_edges.c.child_id, func.count(owner_edges.c.parent_id).label("owners"))
        .group_by(owner_edges.c.child_id)
        .cte("owner_counts")
    )
    root_id = select(document.c.root_id).where(scope(document))
    reachable = root_id.cte("reachable", recursive=True)
    reachable = reachable.union(
        select(owner_edges.c.child_id).select_from(
            reachable.join(owner_edges, owner_edges.c.parent_id == reachable.c.root_id)
        )
    )
    statements.extend(
        (
            SelectInto(
                select(
                    func.coalesce(
                        func.bool_or(
                            func.coalesce(owner_counts.c.owners, 0)
                            != case((native.c.record_id == root_id.scalar_subquery(), 0), else_=1)
                        ),
                        True,
                    ),
                    func.coalesce(func.bool_or(reachable.c.root_id.is_(None)), True),
                )
                .select_from(
                    native.outerjoin(
                        owner_counts, owner_counts.c.child_id == native.c.record_id
                    ).outerjoin(reachable, reachable.c.root_id == native.c.record_id)
                )
                .where(scope(native)),
                ("bad_owner_", "unreachable_"),
            ),
            If(
                core_variable("bad_owner_", Boolean()),
                (Raise("native orphan or repeated containment owner", "23514"),),
            ),
            If(
                core_variable("unreachable_", Boolean()),
                (Raise("native containment cycle or unreachable record", "23514"),),
            ),
        )
    )
    parent, child = access.alias("parent"), access.alias("child")
    children = (
        func.jsonb_array_elements(func.coalesce(parent.c.native_json["children"], empty))
        .table_valued(column("value", JSONB()))
        .lateral("children")
    )
    access_edges = (
        select(
            parent.c.pointer.label("parent_pointer"),
            children.c.value["$ref"].astext.label("child_pointer"),
        )
        .select_from(parent.join(children, true()))
        .where(scope(parent))
        .cte("access_edges")
        .prefix_with("MATERIALIZED", dialect="postgresql")
    )
    missing_child = exists(
        select(1)
        .select_from(
            parent.join(
                child,
                and_(
                    child.c.product_id == parent.c.product_id,
                    child.c.revision_id == parent.c.revision_id,
                    child.c.parent_pointer == parent.c.pointer,
                ),
            )
        )
        .where(
            scope(parent),
            ~exists(
                select(1)
                .select_from(access_edges)
                .where(
                    access_edges.c.parent_pointer == parent.c.pointer,
                    access_edges.c.child_pointer == child.c.pointer,
                )
                .correlate(parent, child)
            ),
        )
    )
    wrong_parent = exists(
        select(1)
        .select_from(
            access_edges.outerjoin(
                child, and_(scope(child), child.c.pointer == access_edges.c.child_pointer)
            )
        )
        .where(
            or_(
                child.c.pointer.is_(None),
                child.c.parent_pointer.is_distinct_from(access_edges.c.parent_pointer),
            ),
        )
    )
    statements.append(
        If(
            select(or_(missing_child, wrong_parent)).add_cte(access_edges).scalar_subquery(),
            (Raise("native parent/child backpointer differs", "23514"),),
        )
    )
    target = model.tables["kb.pdf_record_native"].alias("target")
    statements.append(
        reject(
            select(1)
            .select_from(
                native.join(f, true()).outerjoin(
                    target, and_(scope(target), target.c.record_id == f.c.value["target"].astext)
                )
            )
            .where(
                scope(native), f.c.value["kind"].astext == "object", target.c.record_id.is_(None)
            ),
            "missing native object target",
        )
    )
    counts = (
        select(
            membership.c.parent_id,
            membership.c.field_name,
            func.count().label("count_"),
            func.min(membership.c.ordinal).label("min_"),
            func.max(membership.c.ordinal).label("max_"),
        )
        .where(scope(membership))
        .group_by(membership.c.parent_id, membership.c.field_name)
        .cte("member_counts")
    )
    statements.append(
        reject(
            select(1)
            .select_from(
                native.join(f, true()).outerjoin(
                    counts,
                    and_(counts.c.parent_id == native.c.record_id, counts.c.field_name == f.c.key),
                )
            )
            .where(
                scope(native),
                f.c.value["kind"].astext.in_(("array", "map")),
                or_(
                    func.coalesce(counts.c.count_, 0)
                    != cast(f.c.value["length"].astext, BigInteger()),
                    and_(
                        counts.c.count_ > 0,
                        or_(counts.c.min_ != 0, counts.c.max_ != counts.c.count_ - 1),
                    ),
                ),
            ),
            "native ordered membership incomplete",
        )
    )

    def byte_identity(inline, overflow):
        encoded = func.convert_to(inline, "UTF8")
        return (
            func.coalesce(overflow.c.byte_length, func.octet_length(encoded)),
            func.coalesce(
                overflow.c.byte_root, func.encode(func.ops.pdf_identity_byte_root(encoded), "hex")
            ),
        )

    native_stream, member_stream = stream.alias("address_stream"), stream.alias("member_stream")
    statements.append(
        reject(
            select(1)
            .select_from(
                native.outerjoin(
                    native_stream,
                    and_(
                        scope(native_stream),
                        native_stream.c.stream_id == native.c.native_address_stream_id,
                    ),
                )
            )
            .where(scope(native))
            .group_by(*byte_identity(native.c.native_address, native_stream))
            .having(func.count() > 1),
            "duplicate native address including overflow representation",
        )
    )
    statements.append(
        reject(
            select(1)
            .select_from(
                membership.outerjoin(
                    member_stream,
                    and_(
                        scope(member_stream),
                        member_stream.c.stream_id == membership.c.member_key_stream_id,
                    ),
                )
            )
            .where(
                scope(membership),
                or_(
                    membership.c.member_key.is_not(None),
                    membership.c.member_key_stream_id.is_not(None),
                ),
            )
            .group_by(
                membership.c.parent_id,
                membership.c.field_name,
                *byte_identity(membership.c.member_key, member_stream),
            )
            .having(func.count() > 1),
            "duplicate native map key including overflow representation",
        )
    )
    statements.append(
        reject(
            select(1)
            .select_from(
                reference.outerjoin(
                    native, and_(scope(native), native.c.record_id == reference.c.target_id)
                )
            )
            .where(
                scope(reference),
                or_(
                    native.c.record_id.is_(None),
                    and_(
                        reference.c.native_pointer.is_not(None),
                        reference.c.field_name.not_in(("source_cell_id", "target_cell_id")),
                        not_(
                            func.ops.pdf_reference_bytes_equal(
                                p_build,
                                p_build,
                                native.c.native_address,
                                native.c.native_address_stream_id,
                                reference.c.native_pointer,
                                reference.c.native_pointer_stream_id,
                            )
                        ),
                    ),
                ),
            ),
            "native reference/address target differs",
        )
    )
    c, input_pin = companion.alias("c"), product.alias("input_pin")
    input_context = (
        func.ops.pdf_task_context(input_pin.c.task_id)
        .table_valued(column("project_id", model.tables["ops.data_request"].c.project_id.type))
        .lateral("input_context")
    )
    input_join = c.outerjoin(
        input_pin,
        and_(
            input_pin.c.task_id == cast(c.c.body["task_id"].astext, input_pin.c.task_id.type),
            input_pin.c.product_key == c.c.body["product_key"].astext,
            input_pin.c.content_digest == c.c.body["content_digest"].astext,
        ),
    ).outerjoin(input_context, true())
    statements.append(
        reject(
            select(1)
            .select_from(input_join)
            .where(
                scope(c),
                c.c.family == "input",
                or_(
                    input_pin.c.task_id.is_(None),
                    input_pin.c.artifact_digest.is_distinct_from(p_source),
                    input_context.c.project_id.is_distinct_from(p_project),
                ),
            ),
            "PDF input outside exact admitted source/project custody",
        )
    )
    observation = product_body.alias("observation")
    statements.append(
        reject(
            select(1)
            .select_from(
                c.join(
                    observation,
                    and_(
                        observation.c.task_id
                        == cast(c.c.body["task_id"].astext, observation.c.task_id.type),
                        observation.c.product_key == c.c.body["product_key"].astext,
                    ),
                )
            )
            .where(
                scope(c),
                c.c.family == "input",
                observation.c.descriptor["observation"]["pass_role"].astext.in_(
                    ("chandra_page", "chandra_crop")
                ),
            ),
            "visual observation cannot be an input to selected PDF publication",
        )
    )
    statements.append(
        reject(
            _coverage_support_violation_statement(target_metadata=model),
            "coverage support differs from exact input coverage scope/family/outcome",
        )
    )
    occurrence, item = companion.alias("occurrence"), access.alias("item")
    statements.append(
        reject(
            select(1)
            .select_from(
                occurrence.outerjoin(
                    item, and_(scope(item), item.c.pointer == occurrence.c.body["pointer"].astext)
                )
            )
            .where(
                scope(occurrence),
                occurrence.c.family == "occurrence",
                occurrence.c.body["address_space"].astext.in_(
                    ("native_item", "selected_item", "native_cell")
                ),
                or_(
                    item.c.pointer.is_(None),
                    and_(
                        occurrence.c.body.has_key("cell_index"),
                        cast(occurrence.c.body["cell_index"].astext, BigInteger())
                        >= func.greatest(
                            func.jsonb_array_length(
                                func.coalesce(item.c.native_json["data"]["table_cells"], empty)
                            ),
                            func.jsonb_array_length(
                                func.coalesce(
                                    item.c.native_json["meta"]["tabular_chart"]["chart_data"][
                                        "table_cells"
                                    ],
                                    empty,
                                )
                            ),
                        ),
                    ),
                ),
            ),
            "companion occurrence outside native item/cell inventory",
        )
    )
    e, own, p, old, pr, external = (
        endpoint.alias("e"),
        companion.alias("own"),
        product.alias("p"),
        legacy_occurrence.alias("old"),
        published.alias("pr"),
        companion.alias("external"),
    )
    self_occurrence = exists(
        select(1)
        .select_from(own)
        .where(scope(own), own.c.family == "occurrence", own.c.local_id == e.c.occurrence_id)
        .correlate(e)
    )
    retained_occurrence = exists(
        select(1)
        .select_from(old)
        .where(
            old.c.task_id == p.c.task_id,
            old.c.product_key == p.c.product_key,
            old.c.occurrence_id == e.c.occurrence_id,
        )
        .correlate(p, e)
    )
    published_occurrence = exists(
        select(1)
        .select_from(
            pr.join(
                external,
                and_(
                    external.c.product_id == pr.c.build_id, external.c.revision_id == pr.c.build_id
                ),
            )
        )
        .where(
            pr.c.task_id == p.c.task_id,
            pr.c.product_key == p.c.product_key,
            pr.c.logical_digest == p.c.content_digest,
            external.c.family == "occurrence",
            external.c.local_id == e.c.occurrence_id,
        )
        .correlate(p, e)
    )
    external_occurrence = exists(
        select(1)
        .select_from(p)
        .where(
            p.c.task_id == e.c.target_task_id,
            p.c.product_key == e.c.target_product_key,
            p.c.content_digest == e.c.target_content_digest,
            or_(retained_occurrence, published_occurrence),
        )
        .correlate(e)
    )
    statements.append(
        reject(
            select(1)
            .select_from(e)
            .where(
                scope(e),
                or_(
                    and_(e.c.target_task_id == 0, not_(self_occurrence)),
                    and_(e.c.target_task_id != 0, not_(external_occurrence)),
                ),
            ),
            "companion endpoint outside admitted occurrence inventory",
        )
    )
    metadata_value = companion_field.alias("metadata_value")
    statements.append(
        reject(
            select(1)
            .select_from(c)
            .where(
                scope(c),
                c.c.family == "native_metadata",
                or_(
                    c.c.body.has_key("value"),
                    ~exists(
                        select(1)
                        .select_from(metadata_value)
                        .where(
                            metadata_value.c.product_id == c.c.product_id,
                            metadata_value.c.revision_id == c.c.revision_id,
                            metadata_value.c.family == c.c.family,
                            metadata_value.c.local_id == c.c.local_id,
                            metadata_value.c.field_name == "value",
                        )
                        .correlate(c)
                    ),
                ),
            ),
            "metadata value has no governed byte field",
            "P0001",
        )
    )
    field, field_stream = companion_field.alias("field"), stream.alias("field_stream")
    field_join = field.join(
        c,
        and_(
            *(
                field.c[name] == c.c[name]
                for name in ("product_id", "revision_id", "family", "local_id")
            )
        ),
    ).join(
        field_stream,
        and_(
            field_stream.c.product_id == field.c.product_id,
            field_stream.c.revision_id == field.c.revision_id,
            field_stream.c.stream_id == field.c.stream_id,
        ),
    )
    encoding = case(
        (and_(field.c.field_name == "value", c.c.body["kind"].astext == FAMILY), PROFILE),
        (field.c.field_name.in_(("value", "endpoints")), "pdf-companion-json-field-v1"),
        else_="pdf-record-scalar-v1:s",
    )
    statements.append(
        reject(
            select(1)
            .select_from(field_join)
            .where(
                scope(field),
                or_(
                    c.c.body.has_key(field.c.field_name),
                    field_stream.c.encoding_profile.is_distinct_from(encoding),
                ),
            ),
            "invalid final companion field",
            "P0001",
        )
    )
    statements.append(
        reject(
            select(1)
            .select_from(native)
            .where(
                scope(native),
                native.c.native_type.in_(
                    (
                        "TextItem",
                        "ListItem",
                        "SectionHeaderItem",
                        "FormulaItem",
                        "CodeItem",
                        "GroupItem",
                        "ListGroup",
                        "PictureItem",
                        "TableItem",
                    )
                ),
                native.c.scalars_json.has_key("self_ref"),
                ~exists(
                    select(1)
                    .select_from(access)
                    .where(
                        scope(access), access.c.pointer == native.c.scalars_json["self_ref"].astext
                    )
                    .correlate(native)
                ),
            ),
            "native access inventory incomplete",
        )
    )
    return _publication_control_routine(
        "pdf_check_build_inventory",
        (
            Parameter("p_build", column_type(model.tables["kb.pdf_record_native"].c.product_id)),
            Parameter("p_source", column_type(model.tables["ops.pdf_stage_build"].c.source_digest)),
            Parameter("p_project", column_type(model.tables["ops.data_request"].c.project_id)),
        ),
        pg_type("void"),
        statements,
        (Local("bad_owner_", pg_type("boolean")), Local("unreachable_", pg_type("boolean"))),
        writer=False,
        security_definer=False,
    )
