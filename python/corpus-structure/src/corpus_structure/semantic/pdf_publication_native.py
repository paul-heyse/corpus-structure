"""Forward native publication over immutable PDF records and typed companions."""

from __future__ import annotations

import json
from collections.abc import Mapping
from pathlib import Path

from sqlalchemy import MetaData, Table, case, func, select, union_all
from sqlalchemy.dialects.postgresql import Insert, dialect, insert

from .metadata import metadata as default_metadata
from .native_call_contracts import OperationCallBinding
from .native_program import core_variable
from .pdf_staging import STAGE_FAMILIES

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


def _prepare_pdf_build_sql(
    metadata: MetaData, stages: Mapping[str, str], binding: OperationCallBinding
) -> str:
    from .native_program import (
        Assign,
        Block,
        Local,
        Perform,
        Sql,
        call,
        literal,
        variable,
        void_call_function,
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
    return void_call_function(
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


def _quote(value: str) -> str:
    return "'" + value.replace("'", "''") + "'"


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
    metadata = default_metadata if target_metadata is None else target_metadata
    from sqlalchemy import (
        and_,
        cast,
        column,
        false,
        func,
        literal,
        literal_column,
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
    build = literal_column("p_build", type_=companion.c.product_id.type)
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
                    claims.c.body["supports"], literal_column("'null'::jsonb", type_=JSONB)
                ),
                literal_column("'[]'::jsonb", type_=JSONB),
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


def _published_validation_sql(*, target_metadata=None) -> str:
    from .native_sql_body import published_validation_statement

    body = str(
        published_validation_statement(target_metadata=target_metadata).compile(
            dialect=dialect(), compile_kwargs={"literal_binds": True}
        )
    )
    return (
        "CREATE OR REPLACE FUNCTION ops.read_pdf_published_validation("
        "p_task bigint,p_key text,p_digest text) RETURNS SETOF ops.pdf_build_validation "
        "LANGUAGE sql STABLE SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $$\n"
        + body
        + "\n$$;\n"
    )


def _companion_adoption_sql(context, metadata) -> str:
    """One protected COPY set, exact typed guards and one endpoint target join."""
    from .native_program import Block, function, pg_type
    from .native_shapes import record_shape_predicate
    from .pdf_payload_validation import metadata_classes
    from .pdf_payloads import FAMILY, PROFILE
    from .pdf_shared_streams import (
        part_template,
        pdf_companion_scratch_specs,
        pdf_scratch_prepare,
    )
    from .pdf_staging_native import native_payload_size_sql

    specs = pdf_companion_scratch_specs(metadata)
    relations = [spec.source for spec in specs]
    sql = (
        function(
            "ops",
            "prepare_pdf_companions",
            parameters=(),
            returns=pg_type("void"),
            security_definer=True,
            search_path=("pg_catalog", "pg_temp"),
            body=Block(
                statements=tuple(
                    statement for spec in specs for statement in pdf_scratch_prepare(spec)
                )
            ),
        )
        + ";\n"
    )
    sql += """
CREATE OR REPLACE FUNCTION ops.adopt_pdf_companions(p_build text,p_task bigint,p_attempt bigint,
 p_holder text,p_key text) RETURNS void LANGUAGE plpgsql SECURITY DEFINER
 SET search_path=pg_catalog,pg_temp AS $$
DECLARE b ops.pdf_stage_build; n bigint; size_ bigint; total bigint:=0; total_bytes bigint:=0;
BEGIN
 b:=ops.require_pdf_build(p_build,p_task,p_attempt,p_holder);
 PERFORM ops.require_pdf_operation(b.release_id,'adopt_pdf_companions');
 IF p_key IS NULL OR p_key='' OR octet_length(p_key)>1024 THEN
 RAISE EXCEPTION 'invalid companion replay key' USING ERRCODE='23514'; END IF;
"""
    quote = dialect().identifier_preparer.quote
    for relation in relations:
        scratch = "pg_temp.pc_" + relation.name
        keys = ",".join(quote(c.name) for c in relation.primary_key)
        sql += f"""
 PERFORM ops.require_pdf_stage_scratch('pc_{relation.name}',{part_template(relation)});
 IF EXISTS(SELECT FROM {scratch} WHERE product_id IS DISTINCT FROM p_build OR revision_id IS DISTINCT FROM p_build)
 OR EXISTS(SELECT FROM {scratch} GROUP BY {keys} HAVING count(*)>1) THEN
 RAISE EXCEPTION 'companion upload ownership or duplicate key differs' USING ERRCODE='23514'; END IF;
"""
        if relation.name != "pdf_stage_artifact_part":
            sql += f"""
 SELECT count(*),COALESCE(sum({native_payload_size_sql(relation)}),0) INTO n,size_ FROM {scratch} s;
 total:=total+n; total_bytes:=total_bytes+size_;
 IF total>65536 OR total_bytes>67108864 THEN
 RAISE EXCEPTION 'companion upload profile exceeded' USING ERRCODE='23514'; END IF;
"""
    sql += """
 IF EXISTS(SELECT FROM pg_temp.pc_pdf_stage_endpoint) THEN
 RAISE EXCEPTION 'companion endpoints must be derived natively' USING ERRCODE='23514'; END IF;
 IF EXISTS(SELECT FROM pg_temp.pc_pdf_stage_companion c WHERE c.local_id='' OR c.ordinal<0
 OR jsonb_typeof(c.body) IS DISTINCT FROM 'object' OR octet_length(c.body::text)>65536
 OR (c.family='occurrence' AND c.local_id IS DISTINCT FROM c.body->>'occurrence_id')
 OR (c.family='relation' AND c.local_id IS DISTINCT FROM c.body->>'relation_id')
 OR (c.family='coverage' AND c.local_id IS DISTINCT FROM c.body->>'coverage_id')
 OR (c.family IN ('input','mapping_report') AND c.local_id IS DISTINCT FROM c.ordinal::text)
 OR (c.family='native_metadata' AND c.local_id IS DISTINCT FROM (c.body->>'kind')||':'||(c.body->>'ordinal')))
 OR EXISTS(SELECT FROM pg_temp.pc_pdf_stage_companion c GROUP BY family,
 CASE WHEN family='native_metadata' THEN body->>'kind' ELSE '' END,ordinal HAVING count(*)>1)
 OR EXISTS(SELECT FROM pg_temp.pc_pdf_stage_companion c JOIN ops.pdf_stage_companion old
 ON old.product_id=p_build AND old.family=c.family AND old.ordinal=c.ordinal AND old.local_id<>c.local_id
 AND (c.family<>'native_metadata' OR old.body->>'kind'=c.body->>'kind')) THEN
 RAISE EXCEPTION 'companion identity/order differs from declared semantic row' USING ERRCODE='23514'; END IF;
 IF EXISTS(SELECT FROM pg_temp.pc_pdf_stage_companion_field f
 LEFT JOIN pg_temp.pc_pdf_stage_companion c USING(product_id,revision_id,family,local_id)
 WHERE c.local_id IS NULL OR c.body ? f.field_name
 OR NOT ((f.family='native_metadata' AND f.field_name='value')
 OR (f.family='occurrence' AND f.field_name='text')
 OR (f.family='relation' AND f.field_name IN ('endpoints','evidence')))
 OR f.scalar_kind IS DISTINCT FROM CASE WHEN f.field_name IN ('value','endpoints') THEN 'y' ELSE 's' END) THEN
 RAISE EXCEPTION 'invalid companion external field' USING ERRCODE='23514'; END IF;
"""
    sql += """
 IF EXISTS(SELECT FROM pg_temp.pc_pdf_stage_artifact_stream stream WHERE NOT EXISTS(
 SELECT FROM pg_temp.pc_pdf_stage_companion_field f WHERE f.stream_id=stream.stream_id))
 OR EXISTS(SELECT FROM pg_temp.pc_pdf_stage_artifact_part part WHERE NOT EXISTS(
 SELECT FROM pg_temp.pc_pdf_stage_companion_field f WHERE f.stream_id=part.stream_id)) THEN
 RAISE EXCEPTION 'companion artifact is outside its field inventory' USING ERRCODE='23514'; END IF;
"""

    # Artifact rows are adopted once as sets before the shared byte validator reads
    # them. A later malformed row aborts this entire call/transaction, including parts.
    def adopt(relation, message):
        columns = ",".join(quote(c.name) for c in relation.columns)
        left = ",".join("incoming." + quote(c.name) for c in relation.columns)
        right = ",".join("retained." + quote(c.name) for c in relation.columns)
        keys = " AND ".join(
            "incoming." + quote(c.name) + "=retained." + quote(c.name) for c in relation.primary_key
        )
        return (
            f"IF EXISTS(SELECT FROM pg_temp.pc_{relation.name} incoming JOIN {relation.fullname} retained ON {keys} "
            f"WHERE ROW({left}) IS DISTINCT FROM ROW({right})) THEN RAISE EXCEPTION '{message}' USING ERRCODE='23514'; END IF;\n"
            f"INSERT INTO {relation.fullname}({columns}) SELECT {columns} FROM pg_temp.pc_{relation.name} ON CONFLICT DO NOTHING;\n"
        )

    sql += "PERFORM ops.pdf_adopt_shared_stream_descriptors(p_build,'pg_temp.pc_pdf_stage_artifact_stream'::regclass);\n"
    sql += adopt(relations[2], "changed companion artifact duplicate")
    sql += "PERFORM ops.pdf_adopt_shared_stream_parts(p_build,'pg_temp.pc_pdf_stage_artifact_part'::regclass);\n"
    sql += "PERFORM ops.pdf_verify_shared_stream(p_build,stream_id) FROM pg_temp.pc_pdf_stage_artifact_stream;\n"
    sql += f"""
 IF EXISTS(SELECT FROM pg_temp.pc_pdf_stage_companion_field f
 JOIN pg_temp.pc_pdf_stage_companion c USING(product_id,revision_id,family,local_id)
 LEFT JOIN ops.pdf_stage_artifact_stream stream ON stream.product_id=p_build AND stream.revision_id=p_build AND stream.stream_id=f.stream_id
 WHERE stream.encoding_profile IS DISTINCT FROM CASE
 WHEN f.field_name='value' AND c.body->>'kind'={_quote(FAMILY)} THEN {_quote(PROFILE)}
 WHEN f.field_name IN ('value','endpoints') THEN 'pdf-companion-json-field-v1' ELSE 'pdf-record-scalar-v1:s' END) THEN
 RAISE EXCEPTION 'companion field encoding differs' USING ERRCODE='23514'; END IF;
 PERFORM sum(octet_length(ops.pdf_companion_field_bytes(p_build,p_build,f.stream_id,true)))
 FROM pg_temp.pc_pdf_stage_companion_field f;
"""
    rows = """WITH rows_ AS (
 SELECT c.*,c.body||COALESCE((SELECT jsonb_object_agg(f.field_name,
 CASE WHEN f.field_name='endpoints' THEN convert_from(ops.pdf_companion_field_bytes(p_build,p_build,f.stream_id,true),'UTF8')::jsonb
 ELSE to_jsonb(convert_from(ops.pdf_companion_field_bytes(p_build,p_build,f.stream_id,true),'UTF8')) END)
 FROM pg_temp.pc_pdf_stage_companion_field f WHERE f.family=c.family AND f.local_id=c.local_id
 AND f.field_name IN ('text','endpoints','evidence')),'{}'::jsonb) body_
 FROM pg_temp.pc_pdf_stage_companion c) """
    for family, cls in (
        ("input", "PdfProductInput"),
        ("occurrence", "PdfProductOccurrence"),
        ("relation", "PdfProductRelation"),
        ("coverage", "PdfProductCoverage"),
        ("mapping_report", "PdfMappingDisposition"),
        ("request_outcome", "PdfRecognitionObservation"),
    ):
        invalid = record_shape_predicate(context.boundary, cls, "c.body_")
        sql += f"IF EXISTS({rows} SELECT FROM rows_ c WHERE c.family={_quote(family)} AND ({invalid})) THEN RAISE EXCEPTION 'parsing record shape differs: {cls}' USING ERRCODE='23514'; END IF;\n"
    for cls, where in (
        ("PdfRecordNativeHealth", "c.body ? 'conversion'"),
        ("PdfProductHealth", "NOT c.body ? 'conversion'"),
    ):
        invalid = record_shape_predicate(context.boundary, cls, "c.body")
        sql += f"IF EXISTS(SELECT FROM pg_temp.pc_pdf_stage_companion c WHERE c.family='health' AND ({where}) AND ({invalid})) THEN RAISE EXCEPTION 'parsing record shape differs: {cls}' USING ERRCODE='23514'; END IF;\n"
    classes = metadata_classes()
    sql += f"""
 IF EXISTS(SELECT FROM pg_temp.pc_pdf_stage_companion c WHERE c.family='native_metadata' AND (
 c.body->>'kind' NOT IN ({",".join(_quote(kind) for kind in classes)})
 OR c.body-(CASE WHEN c.body->>'kind'='formula_outcomes' THEN ARRAY['kind','ordinal','pointer','outcome','has_diagnostic']
 WHEN c.body->>'kind'={_quote(FAMILY)} THEN ARRAY['kind','ordinal','pointer','page_no','payload_schema_digest','payload_codec','payload_logical_digest']
 ELSE ARRAY['kind','ordinal','pointer'] END)<>'{{}}'::jsonb
 OR jsonb_typeof(c.body->'ordinal') IS DISTINCT FROM 'number' OR COALESCE(c.body->>'ordinal','')!~'^[0-9]+$'
 OR NOT EXISTS(SELECT FROM pg_temp.pc_pdf_stage_companion_field f WHERE f.family=c.family AND f.local_id=c.local_id AND f.field_name='value')
 OR (c.body->>'kind'='formula_outcomes' AND (jsonb_typeof(c.body->'has_diagnostic') IS DISTINCT FROM 'boolean' OR jsonb_typeof(c.body->'outcome') IS DISTINCT FROM 'string'))
 OR (c.body->>'kind'={_quote(FAMILY)} AND (c.body->>'payload_codec' IS DISTINCT FROM {_quote(PROFILE)}
 OR jsonb_typeof(c.body->'page_no') IS DISTINCT FROM 'number' OR COALESCE(c.body->>'page_no','')!~'^[1-9][0-9]*$'
 OR COALESCE(c.body->>'payload_schema_digest','')!~'^[0-9a-f]{{64}}$' OR COALESCE(c.body->>'payload_logical_digest','')!~'^[0-9a-f]{{64}}$')))) THEN
 RAISE EXCEPTION 'invalid metadata envelope' USING ERRCODE='23514'; END IF;
"""
    properties, alternatives = {}, []
    for property_ in ("pointer", "prose_pointer", "table_pointer"):
        alternatives.append(
            "jsonb_build_object('required',jsonb_build_array("
            + _quote(property_)
            + "),'properties',"
            + _quote(json.dumps(properties))
            + "::jsonb||jsonb_build_object("
            + _quote(property_)
            + ",jsonb_build_object('type','string','const',c.body->'pointer')))"
        )
        properties[property_] = {"not": {"type": "string"}}
    projection = (
        "CASE WHEN c.body ? 'pointer' THEN jsonb_build_object('anyOf',jsonb_build_array("
        + ",".join(alternatives)
        + ")) ELSE "
        + _quote(json.dumps({"properties": properties}))
        + "::jsonb END"
    )
    formula = "CASE WHEN c.body->>'kind'='formula_outcomes' THEN jsonb_build_object('required',jsonb_build_array('outcome'),'properties',jsonb_build_object('outcome',jsonb_build_object('const',c.body->'outcome')))||CASE WHEN c.body->'has_diagnostic'='true'::jsonb THEN jsonb_build_object('required',jsonb_build_array('outcome','error')) ELSE jsonb_build_object('not',jsonb_build_object('required',jsonb_build_array('error'))) END ELSE '{}'::jsonb END"
    for kind, cls in classes.items():
        if kind == FAMILY:
            continue
        schema = _quote(_schema_json(context.boundary.json_schema(cls)))
        sql += f"""
 IF EXISTS(SELECT FROM pg_temp.pc_pdf_stage_companion c JOIN pg_temp.pc_pdf_stage_companion_field f
 USING(product_id,revision_id,family,local_id) WHERE c.family='native_metadata' AND c.body->>'kind'={_quote(kind)} AND f.field_name='value'
 AND public.json_matches_schema(({schema}::jsonb||jsonb_build_object('allOf',jsonb_build_array(({projection}),({formula}))))::json,
 convert_from(ops.pdf_companion_field_bytes(p_build,p_build,f.stream_id,true),'UTF8')::json) IS NOT TRUE) THEN
 RAISE EXCEPTION 'metadata value/schema/projection differs: {cls}' USING ERRCODE='23514'; END IF;
"""
    sql += adopt(relations[0], "changed companion duplicate")
    sql += adopt(relations[1], "changed companion field duplicate")
    sql += """
 IF EXISTS(SELECT FROM pg_temp.pc_pdf_stage_companion c WHERE
 (SELECT count(*) FROM ops.pdf_stage_companion_field f WHERE f.product_id=p_build AND f.family=c.family AND f.local_id=c.local_id)
 <>(SELECT count(*) FROM pg_temp.pc_pdf_stage_companion_field f WHERE f.family=c.family AND f.local_id=c.local_id)) THEN
 RAISE EXCEPTION 'changed companion field inventory' USING ERRCODE='23514'; END IF;
"""
    sql += (
        """INSERT INTO pg_temp.pc_pdf_stage_endpoint
 """
        + rows
        + """
 SELECT p_build,p_build,c.local_id,(endpoint.ordinality-1)::bigint,
 CASE WHEN endpoint.value ? 'input_index' THEN COALESCE((input.body->>'task_id')::bigint,0) ELSE 0 END,
 CASE WHEN endpoint.value ? 'input_index' THEN COALESCE(input.body->>'product_key','@missing') ELSE '@self' END,
 CASE WHEN endpoint.value ? 'input_index' THEN COALESCE(input.body->>'content_digest','@missing') ELSE '@self' END,
 endpoint.value->>'occurrence_id',endpoint.value->>'role'
 FROM rows_ c CROSS JOIN LATERAL jsonb_array_elements(c.body_->'endpoints') WITH ORDINALITY endpoint(value,ordinality)
 LEFT JOIN ops.pdf_stage_companion input ON input.product_id=p_build AND input.family='input' AND input.local_id=endpoint.value->>'input_index'
 WHERE c.family='relation';
 IF EXISTS(SELECT FROM pg_temp.pc_pdf_stage_endpoint WHERE target_content_digest='@missing') THEN
 RAISE EXCEPTION 'companion endpoint input is outside the admitted input inventory' USING ERRCODE='23514'; END IF;
"""
    )
    sql += adopt(relations[4], "changed companion endpoint duplicate")
    from .pdf_staging import stage_upload_profile

    profile = stage_upload_profile()
    return (
        (sql + "END $$;\n")
        .replace("total>65536", "total>" + str(profile["max_rows"]))
        .replace("total_bytes>67108864", "total_bytes>" + str(profile["max_native_bytes"]))
        .replace(
            "octet_length(p_key)>1024",
            "octet_length(p_key)>" + str(profile["max_replay_key_bytes"]),
        )
    )


def publication_sql(*, target_metadata=None, pdf_domain=None) -> str:
    metadata = default_metadata if target_metadata is None else target_metadata
    from .pdf_companion_read_native import (
        pdf_companion_field_read_sql,
        pdf_native_record_shape_sql,
    )
    from .pdf_contracts import _context_from_domain, trusted_pdf_context
    from .pdf_payloads import FAMILY, PROFILE
    from .pdf_validation_read_native import pdf_validation_native_programs
    from .pdf_domain import pdf_call_bindings
    from .pdf_publication_read_native import (
        pdf_publication_projection_sql,
        pdf_record_scope_health_sql,
        pdf_reference_bytes_equal_sql,
    )
    from .pdf_record_reader_native import (
        pdf_companion_export_sql,
        pdf_native_export_sql,
        pdf_record_context_sql,
        pdf_record_reader_sql,
    )

    stage = {
        **STAGE_FAMILIES,
        "companion": "ops.pdf_stage_companion",
        "endpoint": "ops.pdf_stage_endpoint",
        "companion_field": "ops.pdf_stage_companion_field",
        "access": "ops.pdf_stage_access",
        "region": "ops.pdf_stage_region",
    }
    schema_bytes = (
        None
        if pdf_domain is None
        else pdf_domain.source("implementation/pdf/docling-validation.schema.json").content
    )
    sql = (
        pdf_native_record_shape_sql(schema_bytes)
        + pdf_companion_field_read_sql(metadata)
        + pdf_freeze_native_sql(metadata, stage, pdf_domain=pdf_domain)
    )
    context = trusted_pdf_context() if pdf_domain is None else _context_from_domain(None, pdf_domain)
    sql += _companion_adoption_sql(context, metadata) + pdf_reference_bytes_equal_sql(metadata)
    (prepare_binding,) = (
        binding
        for action, binding in pdf_call_bindings(pdf_domain)
        if action == "prepare_pdf_build" and binding.id == "prepare_pdf_build"
    )
    sql += _prepare_pdf_build_sql(metadata, stage, prepare_binding) + ";\n"
    sql += """
CREATE OR REPLACE FUNCTION ops.read_pdf_published_revision(p_task bigint,p_key text,p_digest text)
RETURNS SETOF ops.pdf_published_revision LANGUAGE sql STABLE SECURITY DEFINER SET \
search_path=pg_catalog,pg_temp AS $$
 SELECT p.* FROM ops.pdf_published_revision p JOIN ops.pdf_stage_build b USING(build_id)
 WHERE p.task_id=p_task AND p.product_key=p_key AND p.logical_digest=p_digest AND \
b.state='published'
$$;
"""
    reader = (
        pdf_record_reader_sql()
        + pdf_record_context_sql()
        + pdf_native_export_sql()
        + pdf_companion_export_sql()
    )
    private = pdf_record_reader_sql()
    private = private[: private.index("REVOKE ALL")]
    private = private.replace(
        "ops.read_pdf_record_rows(p_task bigint,p_product text,p_digest text,",
        "ops.read_pdf_frozen_rows(p_build text,p_task bigint,p_attempt bigint,p_holder \
text,p_frozen text,",
    )
    private = private.replace(
        "p_family text,p_filters jsonb,p_after jsonb,p_limit integer)",
        "p_family text,p_after jsonb,p_limit integer,p_filters jsonb DEFAULT '{}'::jsonb)",
    )
    private = private.replace(
        "DECLARE published ops.pdf_published_revision;",
        "DECLARE published ops.pdf_stage_build;",
    )
    private = private.replace(
        "SELECT * INTO STRICT published FROM ops.read_pdf_published_revision(p_task,p_product,p_d\
igest);",
        "published:=ops.require_pdf_frozen(p_build,p_task,p_attempt,p_holder,p_frozen);",
    )
    # A callback needs native reconstruction and selected metadata, not the
    # independent SQL validator's complete relational inventory. Use the same
    # keyed reader and a bounded set of actual referenced stream identities.
    private = private.replace(
        "ARRAY['stream_id']::text[]", "ARRAY['stream_id','stream_ids']::text[]"
    ).replace(
        "(NOT p_filters ? 'stream_id' OR r.stream_id=p_filters->>'stream_id')",
        "(NOT p_filters ? 'stream_id' OR r.stream_id=p_filters->>'stream_id') "
        "AND (NOT p_filters ? 'stream_ids' OR r.stream_id=ANY(ARRAY(SELECT "
        "jsonb_array_elements_text(p_filters->'stream_ids'))))",
    )
    sql += private
    validation_programs = pdf_validation_native_programs(metadata, pdf_domain=pdf_domain)
    sql += (
        validation_programs["validation_contract"]
        + validation_programs["projection_contract"]
        + pdf_inventory_native_sql(metadata)
        + validation_programs["check_build"]
    )

    sql += (
        reader
        + "\n"
        + (Path(__file__).with_name("sql") / "pdf_record_context.sql").read_text()
        + "\n"
    )
    # Published views expose the current record product; preparation stays private.
    for suffix in ("access", "region"):
        fields = [
            column.key
            for column in metadata.tables["kb.pdf_record_" + suffix].columns
            if column.key not in ("product_id", "revision_id")
        ]
        view = "ops.pdf_published_" + ("item" if suffix == "access" else "region")
        sql += (
            f"CREATE OR REPLACE VIEW\
 {view} AS SELECT p.task_id,p.product_key,"
            + ",".join("r." + c for c in fields)
            + f" FROM kb.pdf_record\
_{suffix} r JOIN ops.pdf_published_revision p ON r.product_id=p.build_id;\n"
        )
        sql += f"ALTER VIEW\
 {view} OWNER TO corpus_sem_publisher; GRANT SELECT \
ON {view} TO corpus_sem_writer,corpus_sem_reader,corpus_sem_evaluator;\n"
    sql += """CREATE OR REPLACE VIEW ops.pdf_selected_product AS
 SELECT p.task_id,p.product_key,p.logical_digest AS content_digest,p.release_id,
 contract_input.content_digest AS contract_digest,p.schema_digest,p.recipe_digest,
 NULL::bigint AS parent_task_id,NULL::text AS parent_product_key,NULL::text AS parent_digest,
 NULL::jsonb AS native_json,(SELECT \
c.body-ARRAY['source_scope','page_start','page_end'] FROM kb.pdf_record_companion c WHERE \
c.product_id=p.build_id AND c.revision_id=p.build_id AND c.family='health' AND \
c.body ? 'source_scope' ORDER BY \
c.ordinal,c.local_id LIMIT 1) AS health,NULL::bytea AS payload
 FROM ops.pdf_published_revision p JOIN ops.pdf_build_validation v ON v.build_id=p.build_id
 JOIN sem.input contract_input ON contract_input.release_id=p.release_id
 AND contract_input.input_kind='dependency'
 AND contract_input.input_name IN ('execution/schema/pdf_products',
 'pdf-domain/schema/pdf_products');
ALTER VIEW ops.pdf_selected_product OWNER TO corpus_sem_publisher;
GRANT SELECT ON ops.pdf_selected_product TO corpus_sem_writer,corpus_sem_reader,corpus_sem_evalua\
tor,corpus_sem_admitter;
"""
    sql += """
"""
    sql += """
CREATE OR REPLACE VIEW ops.pdf_published_coverage AS
 WITH coverage_ AS MATERIALIZED (
 SELECT p.task_id,p.product_key,(ops.pdf_companion_body(c.product_id,c.revision_id,c.family,c.loc\
al_id,c.body))->'value' value
 FROM kb.pdf_record_companion c JOIN ops.pdf_published_revision p ON p.build_id=c.product_id
 WHERE c.family='native_metadata' AND c.body->>'kind'='recognition_coverage')
 SELECT task_id,product_key,value->>'section_pointer' AS section_pointer,
 value->>'membership' AS membership,value->>'universe' AS universe,
 value->>'outcome' AS outcome,value->>'policy' AS policy FROM coverage_;
ALTER VIEW ops.pdf_published_coverage OWNER TO corpus_sem_publisher;
GRANT SELECT ON ops.pdf_published_coverage TO corpus_sem_writer,corpus_sem_reader,corpus_sem_eval\
uator;
"""
    sql += pdf_record_scope_health_sql(metadata)
    sql += pdf_publication_projection_sql(metadata)
    from .pdf_certification_native import pdf_certification_native_sql

    sql += pdf_validation_and_seal_native_sql(metadata, pdf_domain=pdf_domain)
    sql += pdf_publication_controls_sql(metadata)
    sql += pdf_certification_native_sql(target_metadata=metadata)
    sql += _published_validation_sql(target_metadata=metadata)
    signatures = [
        "check_pdf_build(text,bigint,bigint,text,text,text)",
        "pdf_validation_contract(text)",
        "pdf_projection_contract(text,text)",
        "prepare_pdf_companions()",
        "adopt_pdf_companions(text,bigint,bigint,text,text)",
        "prepare_pdf_build(text,bigint,bigint,text,text)",
        "read_pdf_frozen_rows(text,bigint,bigint,text,text,text,jsonb,integer,jsonb)",
        "read_pdf_published_revision(bigint,text,text)",
        "read_pdf_published_validation(bigint,text,text)",
    ]
    for signature in signatures:
        sql += f"REVOKE ALL ON FUNCTION ops.{signature} FROM PUBLIC;\n"
        if not signature.startswith("require_"):
            sql += f"GRANT EXECUTE ON FUNCTION ops.{signature} TO corpus_sem_writer;\n"
    sql += "GRANT EXECUTE ON FUNCTION ops.read_pdf_published_revision(bigint,text,text) TO \
corpus_sem_reader,corpus_sem_evaluator;\n"
    sql += "GRANT EXECUTE ON FUNCTION ops.read_pdf_published_validation(bigint,text,text) TO \
corpus_sem_reader,corpus_sem_evaluator;\n"
    return (
        sql.replace("'{pdf_payload_profile}'", _quote(PROFILE))
        .replace("'{pdf_payload_family}'", _quote(FAMILY))
    )


def pdf_record_logical_identity_sql() -> str:
    """Render the native identity template with the same model-owned payload codec."""
    from .pdf_payloads import FAMILY, PROFILE

    sql = Path(__file__).with_name("sql").joinpath("pdf_record_logical_identity.sql").read_text()
    return sql.replace("'{pdf_payload_profile}'", _quote(PROFILE)).replace(
        "'{pdf_payload_family}'", _quote(FAMILY)
    )


def pdf_freeze_native_sql(model, stages=None, *, pdf_domain=None):
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
    return "\n".join(out)


def _publication_control_routine(name, parameters, returns, statements, locals_, *, writer=True, security_definer=True):
    from pglast import ast, enums, parse_sql
    from pglast.stream import RawStream

    from .native_program import Block, function

    declaration = parse_sql(
        function(
            "ops",
            name,
            parameters=parameters,
            returns=returns,
            body=Block(tuple(statements), tuple(locals_)),
            security_definer=security_definer,
            search_path=("pg_catalog", "pg_temp"),
        )
    )[0].stmt
    if not isinstance(declaration, ast.CreateFunctionStmt):
        raise ValueError("PDF frozen custody requires a typed function declaration")
    identity = ast.ObjectWithArgs(
        objname=(ast.String(sval="ops"), ast.String(sval=name)),
        objargs=tuple(parameter.type_ for parameter in parameters),
        args_unspecified=False,
    )
    statements_ = [
        declaration,
        ast.GrantStmt(
            is_grant=False,
            targtype=enums.GrantTargetType.ACL_TARGET_OBJECT,
            objtype=enums.ObjectType.OBJECT_FUNCTION,
            objects=(identity,),
            grantees=(ast.RoleSpec(roletype=enums.RoleSpecType.ROLESPEC_PUBLIC),),
            grant_option=False,
            behavior=enums.DropBehavior.DROP_RESTRICT,
        ),
    ]
    if writer:
        statements_.append(
            ast.GrantStmt(
                is_grant=True,
                targtype=enums.GrantTargetType.ACL_TARGET_OBJECT,
                objtype=enums.ObjectType.OBJECT_FUNCTION,
                objects=(identity,),
                privileges=(ast.AccessPriv(priv_name="execute"),),
                grantees=(
                    ast.RoleSpec(
                        roletype=enums.RoleSpecType.ROLESPEC_CSTRING, rolename="corpus_sem_writer"
                    ),
                ),
                behavior=enums.DropBehavior.DROP_RESTRICT,
            )
        )
    return ";\n".join(RawStream()(statement) for statement in statements_) + ";\n"


def pdf_publication_controls_sql(model):
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
    return "\n".join(out)


def _projection_write_levels(model, pdf_domain):
    import yaml

    from .pdf_contracts import _context_from_domain, trusted_pdf_context

    context = (
        trusted_pdf_context() if pdf_domain is None else _context_from_domain(None, pdf_domain)
    )
    policy_source = yaml.safe_load(model.info["physical_sources"]["pdf-staging.yaml"])[
        "annotations"
    ]["pds:projection_write_profile"]
    policy = context.boundary.validate_json("PdfProjectionWriteProfile", policy_source)
    return sorted(set(policy.model_dump(mode="json")["allowed_isolation"]))


def pdf_validation_and_seal_native_sql(model, *, pdf_domain=None):
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
    return validate + "\n" + seal


def pdf_inventory_native_sql(model):
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
        return func.jsonb_each(relation.c.structure_json["fields"]).table_valued(
            column("key", Text()), column("value", JSONB())
        ).lateral("fields")

    def reject(query, message, state="23514"):
        return If(exists(query), (Raise(message, state),))

    f = fields(native)
    scalar_keys = func.jsonb_object_keys(native.c.scalars_json).table_valued(column("key", Text())).render_derived()
    statements: list[Statement] = [
        reject(select(1).select_from(native).where(scope(native), func.ops.pdf_native_record_shape(native.c.native_type, native.c.scalars_json, native.c.structure_json["fields"]).is_not(True)), "native schema field/required/primitive constraint differs"),
        reject(select(1).select_from(native).where(scope(native), or_(
            func.jsonb_typeof(native.c.structure_json["fields"]).is_distinct_from("object"),
            exists(select(1).select_from(f).where(f.c.value["kind"].astext.not_in(("object", "array", "map", "parts")))),
            exists(select(1).select_from(scalar_keys).where(native.c.structure_json["fields"].has_key(scalar_keys.c.key))),
        )), "invalid native field decomposition"),
        reject(select(1).select_from(membership.outerjoin(native, and_(scope(native), native.c.record_id == membership.c.parent_id))).where(scope(membership),
            or_(native.c.record_id.is_(None), native.c.structure_json["fields"][membership.c.field_name]["kind"].astext.not_in(("array", "map")))), "membership outside declared collection"),
        reject(select(1).select_from(native).where(scope(native), native.c.scalars_json.has_key("self_ref")).group_by(native.c.scalars_json["self_ref"].astext).having(func.count() != 1), "native self-reference is not unique"),
    ]
    ref_index = select(reference.c.reference_id, reference.c.source_id, reference.c.native_pointer, reference.c.native_pointer_stream_id).where(
        scope(reference), reference.c.field_name == "$ref"
    ).cte("ref_index").prefix_with("MATERIALIZED", dialect="postgresql")
    reference_spelling = case((and_(ref_index.c.native_pointer_stream_id.is_(None), native.c.structure_json["fields"]["$ref"]["stream_id"].astext.is_(None)),
        (ref_index.c.native_pointer.collate("C") == native.c.scalars_json["$ref"].astext.collate("C")).is_not(True)),
        else_=not_(func.ops.pdf_reference_bytes_equal(p_build, p_build, ref_index.c.native_pointer, ref_index.c.native_pointer_stream_id, native.c.scalars_json["$ref"].astext, native.c.structure_json["fields"]["$ref"]["stream_id"].astext)))
    statements.append(reject(select(1).select_from(native.outerjoin(ref_index, ref_index.c.source_id == native.c.record_id)).where(
        scope(native), native.c.native_type.in_(("RefItem", "FineRef")), or_(ref_index.c.reference_id.is_(None), reference_spelling)),
        "native reference index does not correspond to supplied spelling"))

    owner_edges = union_all(
        select(native.c.record_id.label("parent_id"), f.c.value["target"].astext.label("child_id")).select_from(native.join(f, true())).where(scope(native), f.c.value["kind"].astext == "object"),
        select(membership.c.parent_id, membership.c.record_id).where(scope(membership), membership.c.value_kind == "record"),
    ).cte("owner_edges").prefix_with("MATERIALIZED", dialect="postgresql")
    owner_counts = select(owner_edges.c.child_id, func.count(owner_edges.c.parent_id).label("owners")).group_by(owner_edges.c.child_id).cte("owner_counts")
    root_id = select(document.c.root_id).where(scope(document))
    reachable = root_id.cte("reachable", recursive=True)
    reachable = reachable.union(select(owner_edges.c.child_id).select_from(reachable.join(owner_edges, owner_edges.c.parent_id == reachable.c.root_id)))
    statements.extend((
        SelectInto(select(
            func.coalesce(func.bool_or(func.coalesce(owner_counts.c.owners, 0) != case((native.c.record_id == root_id.scalar_subquery(), 0), else_=1)), True),
            func.coalesce(func.bool_or(reachable.c.root_id.is_(None)), True),
        ).select_from(native.outerjoin(owner_counts, owner_counts.c.child_id == native.c.record_id).outerjoin(reachable, reachable.c.root_id == native.c.record_id)).where(scope(native)), ("bad_owner_", "unreachable_")),
        If(core_variable("bad_owner_", Boolean()), (Raise("native orphan or repeated containment owner", "23514"),)),
        If(core_variable("unreachable_", Boolean()), (Raise("native containment cycle or unreachable record", "23514"),)),
    ))
    parent, child = access.alias("parent"), access.alias("child")
    children = func.jsonb_array_elements(func.coalesce(parent.c.native_json["children"], empty)).table_valued(column("value", JSONB())).lateral("children")
    missing_child = exists(select(1).select_from(parent.join(child, and_(child.c.product_id == parent.c.product_id, child.c.revision_id == parent.c.revision_id, child.c.parent_pointer == parent.c.pointer))).where(scope(parent),
        ~exists(select(1).select_from(children).where(children.c.value["$ref"].astext == child.c.pointer).correlate(parent, child))))
    wrong_parent = exists(select(1).select_from(parent.join(children, true()).outerjoin(child, and_(scope(child), child.c.pointer == children.c.value["$ref"].astext))).where(scope(parent),
        or_(child.c.pointer.is_(None), child.c.parent_pointer.is_distinct_from(parent.c.pointer))))
    statements.append(If(or_(missing_child, wrong_parent), (Raise("native parent/child backpointer differs", "23514"),)))
    target = model.tables["kb.pdf_record_native"].alias("target")
    statements.append(reject(select(1).select_from(native.join(f, true()).outerjoin(target, and_(scope(target), target.c.record_id == f.c.value["target"].astext))).where(scope(native), f.c.value["kind"].astext == "object", target.c.record_id.is_(None)), "missing native object target"))
    counts = select(membership.c.parent_id, membership.c.field_name, func.count().label("count_"), func.min(membership.c.ordinal).label("min_"), func.max(membership.c.ordinal).label("max_")).where(scope(membership)).group_by(membership.c.parent_id, membership.c.field_name).cte("member_counts")
    statements.append(reject(select(1).select_from(native.join(f, true()).outerjoin(counts, and_(counts.c.parent_id == native.c.record_id, counts.c.field_name == f.c.key))).where(
        scope(native), f.c.value["kind"].astext.in_(("array", "map")), or_(
            func.coalesce(counts.c.count_, 0) != cast(f.c.value["length"].astext, BigInteger()),
            and_(counts.c.count_ > 0, or_(counts.c.min_ != 0, counts.c.max_ != counts.c.count_ - 1)))), "native ordered membership incomplete"))

    def byte_identity(inline, overflow):
        encoded = func.convert_to(inline, "UTF8")
        return (func.coalesce(overflow.c.byte_length, func.octet_length(encoded)),
                func.coalesce(overflow.c.byte_root, func.encode(func.ops.pdf_identity_byte_root(encoded), "hex")))

    native_stream, member_stream = stream.alias("address_stream"), stream.alias("member_stream")
    statements.append(reject(select(1).select_from(native.outerjoin(native_stream, and_(scope(native_stream), native_stream.c.stream_id == native.c.native_address_stream_id))).where(scope(native)).group_by(
        *byte_identity(native.c.native_address, native_stream)).having(func.count() > 1), "duplicate native address including overflow representation"))
    statements.append(reject(select(1).select_from(membership.outerjoin(member_stream, and_(scope(member_stream), member_stream.c.stream_id == membership.c.member_key_stream_id))).where(scope(membership),
        or_(membership.c.member_key.is_not(None), membership.c.member_key_stream_id.is_not(None))).group_by(membership.c.parent_id, membership.c.field_name,
        *byte_identity(membership.c.member_key, member_stream)).having(func.count() > 1), "duplicate native map key including overflow representation"))
    statements.append(reject(select(1).select_from(reference.outerjoin(native, and_(scope(native), native.c.record_id == reference.c.target_id))).where(scope(reference), or_(
        native.c.record_id.is_(None), and_(reference.c.native_pointer.is_not(None), reference.c.field_name.not_in(("source_cell_id", "target_cell_id")),
            not_(func.ops.pdf_reference_bytes_equal(p_build, p_build, native.c.native_address, native.c.native_address_stream_id, reference.c.native_pointer, reference.c.native_pointer_stream_id))))), "native reference/address target differs"))
    c, input_pin = companion.alias("c"), product.alias("input_pin")
    input_context = func.ops.pdf_task_context(input_pin.c.task_id).table_valued(column("project_id", model.tables["ops.data_request"].c.project_id.type)).lateral("input_context")
    input_join = c.outerjoin(input_pin, and_(input_pin.c.task_id == cast(c.c.body["task_id"].astext, input_pin.c.task_id.type), input_pin.c.product_key == c.c.body["product_key"].astext, input_pin.c.content_digest == c.c.body["content_digest"].astext)).outerjoin(input_context, true())
    statements.append(reject(select(1).select_from(input_join).where(scope(c), c.c.family == "input", or_(input_pin.c.task_id.is_(None), input_pin.c.artifact_digest.is_distinct_from(p_source), input_context.c.project_id.is_distinct_from(p_project))), "PDF input outside exact admitted source/project custody"))
    observation = product_body.alias("observation")
    statements.append(reject(select(1).select_from(c.join(observation, and_(observation.c.task_id == cast(c.c.body["task_id"].astext, observation.c.task_id.type), observation.c.product_key == c.c.body["product_key"].astext))).where(scope(c), c.c.family == "input", observation.c.descriptor["observation"]["pass_role"].astext.in_(("chandra_page", "chandra_crop"))), "visual observation cannot be an input to selected PDF publication"))
    statements.append(reject(_coverage_support_violation_statement(target_metadata=model), "coverage support differs from exact input coverage scope/family/outcome"))
    occurrence, item = companion.alias("occurrence"), access.alias("item")
    statements.append(reject(select(1).select_from(occurrence.outerjoin(item, and_(scope(item), item.c.pointer == occurrence.c.body["pointer"].astext))).where(scope(occurrence), occurrence.c.family == "occurrence", occurrence.c.body["address_space"].astext.in_(("native_item", "selected_item", "native_cell")), or_(item.c.pointer.is_(None),
        and_(occurrence.c.body.has_key("cell_index"), cast(occurrence.c.body["cell_index"].astext, BigInteger()) >= func.greatest(
            func.jsonb_array_length(func.coalesce(item.c.native_json["data"]["table_cells"], empty)),
            func.jsonb_array_length(func.coalesce(item.c.native_json["meta"]["tabular_chart"]["chart_data"]["table_cells"], empty)),
        )))), "companion occurrence outside native item/cell inventory"))
    e, own, p, old, pr, external = endpoint.alias("e"), companion.alias("own"), product.alias("p"), legacy_occurrence.alias("old"), published.alias("pr"), companion.alias("external")
    self_occurrence = exists(select(1).select_from(own).where(scope(own), own.c.family == "occurrence", own.c.local_id == e.c.occurrence_id).correlate(e))
    retained_occurrence = exists(select(1).select_from(old).where(old.c.task_id == p.c.task_id, old.c.product_key == p.c.product_key, old.c.occurrence_id == e.c.occurrence_id).correlate(p, e))
    published_occurrence = exists(select(1).select_from(pr.join(external, and_(external.c.product_id == pr.c.build_id, external.c.revision_id == pr.c.build_id))).where(
        pr.c.task_id == p.c.task_id, pr.c.product_key == p.c.product_key, pr.c.logical_digest == p.c.content_digest,
        external.c.family == "occurrence", external.c.local_id == e.c.occurrence_id).correlate(p, e))
    external_occurrence = exists(select(1).select_from(p).where(p.c.task_id == e.c.target_task_id, p.c.product_key == e.c.target_product_key, p.c.content_digest == e.c.target_content_digest,
        or_(retained_occurrence, published_occurrence)).correlate(e))
    statements.append(reject(select(1).select_from(e).where(scope(e), or_(and_(e.c.target_task_id == 0, not_(self_occurrence)), and_(e.c.target_task_id != 0, not_(external_occurrence)))), "companion endpoint outside admitted occurrence inventory"))
    metadata_value = companion_field.alias("metadata_value")
    statements.append(reject(select(1).select_from(c).where(scope(c), c.c.family == "native_metadata", or_(c.c.body.has_key("value"),
        ~exists(select(1).select_from(metadata_value).where(metadata_value.c.product_id == c.c.product_id, metadata_value.c.revision_id == c.c.revision_id,
            metadata_value.c.family == c.c.family, metadata_value.c.local_id == c.c.local_id, metadata_value.c.field_name == "value").correlate(c)))), "metadata value has no governed byte field", "P0001"))
    field, field_stream = companion_field.alias("field"), stream.alias("field_stream")
    field_join = field.join(c, and_(*(field.c[name] == c.c[name] for name in ("product_id", "revision_id", "family", "local_id")))).join(field_stream, and_(
        field_stream.c.product_id == field.c.product_id, field_stream.c.revision_id == field.c.revision_id, field_stream.c.stream_id == field.c.stream_id))
    encoding = case((and_(field.c.field_name == "value", c.c.body["kind"].astext == FAMILY), PROFILE),
        (field.c.field_name.in_(("value", "endpoints")), "pdf-companion-json-field-v1"), else_="pdf-record-scalar-v1:s")
    statements.append(reject(select(1).select_from(field_join).where(scope(field), or_(c.c.body.has_key(field.c.field_name), field_stream.c.encoding_profile.is_distinct_from(encoding))), "invalid final companion field", "P0001"))
    statements.append(reject(select(1).select_from(native).where(scope(native), native.c.native_type.in_(("TextItem", "ListItem", "SectionHeaderItem", "FormulaItem", "CodeItem", "GroupItem", "ListGroup", "PictureItem", "TableItem")),
        native.c.scalars_json.has_key("self_ref"), ~exists(select(1).select_from(access).where(scope(access), access.c.pointer == native.c.scalars_json["self_ref"].astext).correlate(native))), "native access inventory incomplete"))
    return _publication_control_routine("pdf_check_build_inventory", (
        Parameter("p_build", column_type(model.tables["kb.pdf_record_native"].c.product_id)),
        Parameter("p_source", column_type(model.tables["ops.pdf_stage_build"].c.source_digest)),
        Parameter("p_project", column_type(model.tables["ops.data_request"].c.project_id)),
    ), pg_type("void"), statements, (Local("bad_owner_", pg_type("boolean")), Local("unreachable_", pg_type("boolean"))), writer=False, security_definer=False)
