"""Published-only bounded record access, composed into forward native authoring."""

from sqlalchemy import BigInteger, MetaData, Numeric, Table, Text, cast, column, func, or_, select
from sqlalchemy.dialects.postgresql import JSONB

from .metadata import metadata
from .native_objects import NativeIdentity, native_privilege_sql, native_sql_script
from .native_program import (
    Block,
    If,
    Local,
    Parameter,
    Raise,
    Return,
    SelectInto,
    column_type,
    core_relation_row,
    core_variable,
    function,
    pg_type,
)
from .pdf_record_pages_native import pdf_record_page_sql


def pdf_record_reader_sql(*, target_metadata: MetaData | None = None) -> str:
    model = metadata if target_metadata is None else target_metadata
    return pdf_record_page_sql(model) + pdf_materialization_bound_sql(model)


def pdf_record_context_sql() -> str:
    """Paginate the same relational scope constructor used by set-based consumers."""
    from pathlib import Path

    source = (Path(__file__).with_name("sql") / "pdf_record_context.sql").read_text()
    _, start, remaining = source.partition("-- BEGIN pdf-context-selection\n")
    selection, end, _ = remaining.partition("-- END pdf-context-selection\n")
    if not start or not end:
        raise ValueError("shared PDF context selector markers are missing")
    selection = selection.strip().replace("p_key", "p_product")
    return f"""
CREATE OR REPLACE FUNCTION ops.read_pdf_record_context_rows(
 p_task bigint,p_product text,p_digest text,p_pointers text[],p_section text,
 p_family text,p_after text,p_limit integer)
RETURNS SETOF jsonb LANGUAGE plpgsql SECURITY DEFINER
 SET search_path=pg_catalog,pg_temp AS $reader$
DECLARE placement ops.pdf_published_revision;
BEGIN
 IF p_limit IS NULL OR p_limit NOT BETWEEN 1 AND 1000 OR p_pointers IS NULL OR p_family IS NULL OR
 p_family NOT IN ('occurrence','relation','input','coverage','mapping_report','health') THEN
 RAISE EXCEPTION 'invalid published context page' USING ERRCODE='22023'; END IF;
 SELECT * INTO STRICT placement FROM ops.read_pdf_published_revision(p_task,p_product,p_digest);
 RETURN QUERY
 {selection}, selected_context AS (
   SELECT c.product_id,c.revision_id,c.family,c.local_id,c.body FROM chosen c
   WHERE c.family=p_family
   UNION ALL
   SELECT c.product_id,c.revision_id,c.family,c.local_id,c.body
    FROM kb.pdf_record_companion c JOIN published p
    ON c.product_id=p.build_id AND c.revision_id=p.build_id
    WHERE p_family='health' AND c.family='health'
 ), requested_page AS MATERIALIZED (
   SELECT c.* FROM selected_context c
   WHERE c.local_id>COALESCE(p_after,'')
   ORDER BY c.local_id LIMIT p_limit
 )
 SELECT jsonb_build_object('local_id',c.local_id,'body',
   ops.pdf_companion_body(c.product_id,c.revision_id,c.family,c.local_id,c.body))
 FROM requested_page c ORDER BY c.local_id;
END $reader$;
REVOKE ALL ON FUNCTION
 ops.read_pdf_record_context_rows(bigint,text,text,text[],text,text,text,integer) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION
 ops.read_pdf_record_context_rows(bigint,text,text,text[],text,text,text,integer)
 TO corpus_sem_reader,corpus_sem_writer,corpus_sem_evaluator;
"""


def pdf_native_export_sql() -> str:
    """One ordered cursor over containment, rather than one SQL request per object."""
    return (
        "\n"
        "CREATE OR REPLACE FUNCTION ops.read_pdf_native_events(p_task "
        "bigint,p_product text,p_digest text)\n"
        "RETURNS SETOF jsonb LANGUAGE sql STABLE SECURITY DEFINER SET "
        "search_path=pg_catalog,pg_temp AS $events$\n"
        "WITH RECURSIVE published AS MATERIALIZED (\n"
        " SELECT * FROM ops.read_pdf_published_revision(p_task,p_product,p"
        "_digest)\n"
        "), nodes AS MATERIALIZED (\n"
        " SELECT n.* FROM kb.pdf_record_native n JOIN published p ON "
        "n.product_id=p.build_id AND n.revision_id=p.build_id\n"
        "), members AS MATERIALIZED (\n"
        " SELECT m.* FROM kb.pdf_record_membership m JOIN published p ON "
        "m.product_id=p.build_id AND m.revision_id=p.build_id\n"
        "), fields AS MATERIALIZED (\n"
        " SELECT record_id,name,value,kind,row_number() OVER(PARTITION BY "
        'record_id ORDER BY name COLLATE "C")-1 AS slot\n'
        " FROM (\n"
        " SELECT n.record_id,x.key AS name,x.value,'scalar'::text AS kind "
        "FROM nodes n\n"
        " CROSS JOIN LATERAL jsonb_each(n.scalars_json) x\n"
        " UNION ALL\n"
        " SELECT n.record_id,x.key,x.value,x.value->>'kind' FROM nodes n\n"
        " CROSS JOIN LATERAL jsonb_each(n.structure_json->'fields') x\n"
        " ) f\n"
        "), edges AS MATERIALIZED (\n"
        " SELECT f.record_id AS parent_id,f.value->>'target' AS "
        "child_id,ARRAY[1,f.slot,1]::bigint[] AS suffix\n"
        " FROM fields f WHERE f.kind='object'\n"
        " UNION ALL\n"
        " SELECT m.parent_id,m.record_id,ARRAY[1,f.slot,1,1,m.ordinal,1]::"
        "bigint[] FROM members m\n"
        " JOIN fields f ON f.record_id=m.parent_id AND "
        "f.name=m.field_name WHERE m.value_kind='record'\n"
        "), walk(record_id,path) AS (\n"
        " SELECT h.root_id,ARRAY[]::bigint[] FROM ops.pdf_record_document "
        "h JOIN published p\n"
        " ON h.product_id=p.build_id AND h.revision_id=p.build_id\n"
        " UNION ALL\n"
        " SELECT e.child_id,w.path||e.suffix FROM walk w JOIN edges e ON "
        "e.parent_id=w.record_id\n"
        "), events(path,kind,value,prefix) AS (\n"
        " SELECT w.path||ARRAY[0]::bigint[],'literal',to_jsonb(CASE WHEN "
        "n.native_type='NativeArray' THEN '' ELSE '{' END),''\n"
        " FROM walk w JOIN nodes n USING(record_id)\n"
        " UNION ALL\n"
        " SELECT w.path||ARRAY[1,f.slot,0]::bigint[],'literal',to_jsonb(CA"
        "SE WHEN n.native_type='NativeArray' THEN ''\n"
        " ELSE (CASE WHEN f.slot>0 THEN ',' ELSE '' "
        "END)||to_jsonb(f.name)::text||':' END),''\n"
        " FROM walk w JOIN nodes n USING(record_id) JOIN fields f "
        "USING(record_id)\n"
        " UNION ALL\n"
        " SELECT w.path||ARRAY[1,f.slot,1]::bigint[],CASE WHEN "
        "f.kind='scalar' THEN 'inline' ELSE 'parts' END,\n"
        " CASE WHEN f.kind='scalar' THEN f.value ELSE "
        "to_jsonb(f.value->>'stream_id') END,''\n"
        " FROM walk w JOIN fields f USING(record_id) WHERE f.kind IN "
        "('scalar','parts')\n"
        " UNION ALL\n"
        " SELECT w.path||ARRAY[1,f.slot,1,0]::bigint[],'literal',to_jsonb("
        "CASE WHEN f.kind='map' THEN '{' ELSE '[' END),''\n"
        " FROM walk w JOIN fields f USING(record_id) WHERE f.kind IN "
        "('array','map')\n"
        " UNION ALL\n"
        " SELECT w.path||ARRAY[1,f.slot,1,1,m.ordinal,0]::bigint[],\n"
        " CASE WHEN f.kind='map' AND m.member_key IS NULL THEN "
        "'key_parts' ELSE 'literal' END,\n"
        " CASE WHEN f.kind='map' AND m.member_key IS NULL THEN "
        "to_jsonb(m.member_key_stream_id)\n"
        " ELSE to_jsonb((CASE WHEN m.ordinal>0 THEN ',' ELSE '' END)||\n"
        " CASE WHEN f.kind='map' THEN to_jsonb(m.member_key)::text||':' "
        "ELSE '' END) END,\n"
        " CASE WHEN m.ordinal>0 THEN ',' ELSE '' END\n"
        " FROM walk w JOIN fields f USING(record_id) JOIN members m ON "
        "m.parent_id=f.record_id AND m.field_name=f.name\n"
        " WHERE f.kind IN ('array','map')\n"
        " UNION ALL\n"
        " SELECT w.path||ARRAY[1,f.slot,1,1,m.ordinal,1]::bigint[],\n"
        " CASE WHEN m.value_kind='scalar' THEN 'inline' ELSE 'parts' END,\n"
        " CASE WHEN m.value_kind='scalar' THEN m.scalar_json ELSE "
        "to_jsonb(m.stream_id) END,''\n"
        " FROM walk w JOIN fields f USING(record_id) JOIN members m ON "
        "m.parent_id=f.record_id AND m.field_name=f.name\n"
        " WHERE m.value_kind IN ('scalar','parts')\n"
        " UNION ALL\n"
        " SELECT w.path||ARRAY[1,f.slot,1,2]::bigint[],'literal',to_jsonb("
        "CASE WHEN f.kind='map' THEN '}' ELSE ']' END),''\n"
        " FROM walk w JOIN fields f USING(record_id) WHERE f.kind IN "
        "('array','map')\n"
        " UNION ALL\n"
        " SELECT w.path||ARRAY[1,(SELECT count(*) FROM fields f WHERE "
        "f.record_id=n.record_id),0]::bigint[],\n"
        " 'extension',n.structure_json->'extensions'->'stream_id',\n"
        " CASE WHEN EXISTS(SELECT FROM fields f WHERE "
        "f.record_id=n.record_id) THEN ',' ELSE '' END\n"
        " FROM walk w JOIN nodes n USING(record_id) WHERE "
        "n.structure_json ? 'extensions'\n"
        " UNION ALL\n"
        " SELECT w.path||ARRAY[2]::bigint[],'literal',to_jsonb(CASE WHEN "
        "n.native_type='NativeArray' THEN '' ELSE '}' END),''\n"
        " FROM walk w JOIN nodes n USING(record_id)\n"
        ") SELECT jsonb_build_object('kind',kind,'value',value,'prefix',pr"
        "efix) FROM events ORDER BY path\n"
        "$events$;\n"
        "REVOKE ALL ON FUNCTION "
        "ops.read_pdf_native_events(bigint,text,text) FROM PUBLIC;\n"
        "GRANT EXECUTE ON FUNCTION "
        "ops.read_pdf_native_events(bigint,text,text)\n"
        " TO corpus_sem_reader,corpus_sem_writer,corpus_sem_evaluator;\n"
    )


def pdf_companion_export_sql() -> str:
    """One ordered companion/field/part cursor, including exact overflow payloads."""
    return (
        "\n"
        "CREATE OR REPLACE FUNCTION "
        "ops.read_pdf_companion_export_events(p_task bigint,p_key "
        "text,p_digest text,p_family text)\n"
        "RETURNS SETOF jsonb LANGUAGE sql STABLE SECURITY DEFINER SET "
        "search_path=pg_catalog,pg_temp AS $$\n"
        "WITH published AS MATERIALIZED (\n"
        " SELECT * FROM ops.read_pdf_published_revision(p_task,p_key,p_dig"
        "est)\n"
        "), companions AS MATERIALIZED (\n"
        " SELECT c.* FROM kb.pdf_record_companion c JOIN published p ON "
        "c.product_id=p.build_id AND c.revision_id=p.build_id\n"
        " WHERE c.family=p_family\n"
        "), fields AS MATERIALIZED (\n"
        " SELECT cf.*,c.ordinal AS row_ordinal FROM "
        "kb.pdf_record_companion_field cf\n"
        " JOIN companions c USING(product_id,revision_id,family,local_id)\n"
        "), events(ordinal,local_id,phase,field_name,subphase,part_ordinal"
        ",event) AS (\n"
        " SELECT c.ordinal,c.local_id,0,''::text,0,0::bigint,jsonb_build_o"
        "bject('kind','row','body',c.body) FROM companions c\n"
        " UNION ALL\n"
        " SELECT f.row_ordinal,f.local_id,1,f.field_name,0,0::bigint,jsonb"
        "_build_object('kind','field','field',\n"
        " to_jsonb(s)||jsonb_build_object('field_name',f.field_name,'scala"
        "r_kind',f.scalar_kind))\n"
        " FROM fields f JOIN ops.pdf_artifact_stream s "
        "USING(product_id,revision_id,stream_id)\n"
        " UNION ALL\n"
        " SELECT f.row_ordinal,f.local_id,1,f.field_name,1,part.ordinal,js"
        "onb_build_object('kind','part','part',to_jsonb(part))\n"
        " FROM fields f JOIN LATERAL ops.pdf_artifact_parts(f.product_id,f.revision_id,false,ARRAY[f.stream_id]) part "
        "USING(product_id,revision_id,stream_id)\n"
        " UNION ALL\n"
        " SELECT c.ordinal,c.local_id,2,''::text,0,0::bigint,jsonb_build_o"
        "bject('kind','close') FROM companions c\n"
        ") SELECT event FROM events ORDER BY "
        "ordinal,local_id,phase,field_name,subphase,part_ordinal\n"
        "$$;\n"
        "REVOKE ALL ON FUNCTION "
        "ops.read_pdf_companion_export_events(bigint,text,text,text) FROM "
        "PUBLIC;\n"
        "GRANT EXECUTE ON FUNCTION "
        "ops.read_pdf_companion_export_events(bigint,text,text,text)\n"
        " TO corpus_sem_reader,corpus_sem_writer,corpus_sem_evaluator;\n"
    )


def pdf_native_event_ctes(
    *,
    roots_sql: str,
    published_sql: str,
    additional_ctes: str = "",
    node_filter_sql: str | None = None,
) -> str:
    """Reuse the native event algebra with trusted operation-owned record roots.

    Inputs are SQL authoring fragments, never invocation text. The ordinary complete
    export remains byte compatible. Selected-source seeds multiple roots into this one
    ordered event query rather than invoking a native serializer for each selected item.
    """
    source = pdf_native_export_sql().split("AS $events$\n", 1)[1].split("$events$;", 1)[0]
    published = "SELECT * FROM ops.read_pdf_published_revision(p_task,p_product,p_digest)"
    if source.count(published) != 1:
        raise ValueError("native event publication authoring seam changed")
    source = source.replace(published, published_sql)
    roots = (
        "SELECT h.root_id,ARRAY[]::bigint[] FROM ops.pdf_record_document h JOIN published p\n"
        " ON h.product_id=p.build_id AND h.revision_id=p.build_id"
    )
    if source.count(roots) != 1:
        raise ValueError("native event root authoring seam changed")
    source = source.replace(roots, roots_sql)
    if additional_ctes:
        source = source.replace(
            "), nodes AS MATERIALIZED (", "), " + additional_ctes + ", nodes AS MATERIALIZED (", 1
        )
    if node_filter_sql is not None:
        start = source.index("), nodes AS MATERIALIZED (")
        end = source.index("), members AS MATERIALIZED (", start)
        segment = source[start:end]
        marker = "n.product_id=p.build_id AND n.revision_id=p.build_id\n"
        if segment.count(marker) != 1:
            raise ValueError("native event node authoring seam changed")
        segment = segment.replace(marker, marker.rstrip() + " AND (" + node_filter_sql + ")\n")
        source = source[:start] + segment + source[end:]
        start = source.index("), members AS MATERIALIZED (")
        end = source.index("), fields AS MATERIALIZED (", start)
        segment = source[start:end]
        marker = "m.product_id=p.build_id AND m.revision_id=p.build_id\n"
        if segment.count(marker) != 1:
            raise ValueError("native event membership authoring seam changed")
        segment = segment.replace(
            marker, marker.rstrip() + " AND m.parent_id IN (SELECT record_id FROM nodes)\n"
        )
        source = source[:start] + segment + source[end:]
    marker = ") SELECT jsonb_build_object('kind',kind,'value',value,'prefix',prefix)"
    if source.count(marker) != 1:
        raise ValueError("native event result authoring seam changed")
    return source.split(marker, 1)[0] + ")"


def pdf_companion_event_ctes(*, companions_sql: str, prefix: str) -> str:
    """Reuse exact companion-field/part events for an operation-owned selected set."""
    import re

    if not prefix.isidentifier():
        raise ValueError("companion event CTE prefix must be a trusted SQL identifier")
    source = pdf_companion_export_sql().split("AS $$\n", 1)[1].split("$$;", 1)[0]
    source = source.split("), companions AS MATERIALIZED (", 1)[1]
    source = "companions AS MATERIALIZED (" + source
    start = source.index("(") + 1
    end = source.index("), fields AS MATERIALIZED (")
    source = source[:start] + "\n" + companions_sql + "\n" + source[end:]
    source = source.split(") SELECT event FROM events ORDER BY ", 1)[0] + ")"
    for name in ("companions", "fields", "events"):
        source = re.sub(r"\b" + name + r"\b", prefix + name, source)
    return source


def pdf_materialization_bound_sql(model: MetaData) -> str:
    """Conservatively bound native and companion encoded inputs before transfer."""
    placement = model.tables["ops.pdf_published_revision"]
    task, product, digest = (
        core_variable(name, field.type)
        for name, field in (
            ("p_task", placement.c.task_id),
            ("p_product", placement.c.product_key),
            ("p_digest", placement.c.logical_digest),
        )
    )
    build = core_variable("published", placement.c.build_id.type, "build_id")
    rows = (
        func.ops.read_pdf_published_revision(task, product, digest)
        .table_valued(*(column(field.name, field.type) for field in placement.c))
        .alias("placement")
    )
    read_placement = SelectInto(
        select(core_relation_row(Table("placement", MetaData()))).select_from(rows),
        ("published",),
        strict=True,
    )
    exported = (
        func.ops.read_pdf_native_events(task, product, digest)
        .table_valued(column("event", JSONB()))
        .render_derived()
    )
    events = select(exported.c.event).cte("events").prefix_with("MATERIALIZED")

    def byte_count(value):
        return func.coalesce(func.sum(cast(value, Numeric())), 0)

    def placed(row):
        return row.c.product_id == build, row.c.revision_id == build

    artifacts = model.tables["kb.source_artifact"]
    streams = model.tables["ops.pdf_artifact_stream"]
    event_bytes = select(byte_count(func.octet_length(cast(events.c.event, Text()))))
    # Count repeated native stream uses individually, including escaped JSON strings.
    native_bytes = (
        select(byte_count(streams.c.byte_length))
        .select_from(events.join(streams, streams.c.stream_id == events.c.event["value"].astext))
        .where(
            *placed(streams), events.c.event["kind"].astext.in_(("parts", "key_parts", "extension"))
        )
    )
    companion_stream_bytes = select(byte_count(streams.c.byte_length)).where(*placed(streams))
    record_bytes = []
    for name in ("companion", "companion_field", "membership"):
        row = model.tables[f"kb.pdf_record_{name}"]
        size = func.octet_length(cast(func.to_jsonb(row.table_valued()), Text()))
        record_bytes.append(select(byte_count(size)).where(*placed(row)))
    raw_bytes = select(byte_count(func.octet_length(artifacts.c.content))).where(
        artifacts.c.artifact_digest.in_(
            tuple(
                core_variable("published", placement.c[name].type, name)
                for name in ("source_digest", "schema_digest", "recipe_digest")
            )
        )
    )
    # A JSON string may take six encoded bytes per input byte.
    escaped = (
        sum(
            query.scalar_subquery()
            for query in (event_bytes, native_bytes, companion_stream_bytes, *record_bytes)
        )
        * 6
    )
    total = core_variable("total", Numeric())
    name = "read_pdf_materialization_bound"
    definition = function(
        "ops",
        name,
        parameters=(
            Parameter("p_task", column_type(placement.c.task_id)),
            Parameter("p_product", column_type(placement.c.product_key)),
            Parameter("p_digest", column_type(placement.c.logical_digest)),
        ),
        returns=pg_type("int8"),
        security_definer=True,
        search_path=("pg_catalog", "pg_temp"),
        volatility="stable",
        body=Block(
            (
                read_placement,
                SelectInto(select(escaped + raw_bytes.scalar_subquery()), ("total",)),
                If(
                    or_(total.is_(None), total < 0, total > 2**63 - 1),
                    (Raise("PDF materialization bound exceeds signed integer capacity", "22003"),),
                ),
                Return(cast(total, BigInteger())),
            ),
            (Local("published", placement), Local("total", pg_type("numeric"))),
        ),
    )
    identity = NativeIdentity("function", "ops", name, ("bigint", "text", "text"))
    return (
        native_sql_script(
            (
                definition,
                native_privilege_sql(identity, "PUBLIC", grant=False),
                *(
                    native_privilege_sql(identity, role, "execute")
                    for role in ("corpus_sem_reader", "corpus_sem_writer", "corpus_sem_evaluator")
                ),
            )
        )
        + "\n"
    )
