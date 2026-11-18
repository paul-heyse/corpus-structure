"""Protected selected membership/context over the existing native event algebra."""

import json
from importlib.resources import files

import yaml
from pglast import ast, parse_sql
from pglast.stream import RawStream
from sqlalchemy import MetaData, Text, column, select, table
from sqlalchemy.dialects.postgresql import array, dialect

from .native_program import core_variable
from .pdf_record_reader_native import pdf_companion_event_ctes, pdf_native_event_ctes


def selected_membership_relations(metadata: MetaData, *, section=None):
    """Pin access rows before traversing descendants and ancestors."""
    source = metadata.tables["kb.pdf_record_access"].alias("a")
    published = table("published", column("build_id", source.c.product_id.type))
    root = core_variable("p_section", Text()) if section is None else section
    access = (
        select(source)
        .join(
            published,
            (source.c.product_id == published.c.build_id)
            & (source.c.revision_id == published.c.build_id),
        )
        .cte("access")
        .prefix_with("MATERIALIZED")
    )
    subtree = (
        select(access.c.pointer).where(access.c.pointer == root).cte("subtree", recursive=True)
    )
    child = access.alias("child")
    subtree = subtree.union_all(
        select(child.c.pointer).join(subtree, child.c.parent_pointer == subtree.c.pointer)
    )
    selected = (
        select(access)
        .where(access.c.pointer.in_(select(subtree.c.pointer)))
        .cte("selected")
        .prefix_with("MATERIALIZED")
    )
    ancestors = (
        select(access.c.parent_pointer.label("pointer"))
        .where(access.c.pointer == root, access.c.parent_pointer.is_not(None))
        .cte("ancestors", recursive=True)
    )
    parent = access.alias("ancestor_access")
    ancestors = ancestors.union(
        select(parent.c.parent_pointer)
        .join(ancestors, parent.c.pointer == ancestors.c.pointer)
        .where(parent.c.parent_pointer.is_not(None))
    )
    return access, subtree, selected, ancestors


def _selected_membership_sql(metadata: MetaData):
    access, subtree, selected, ancestors = selected_membership_relations(metadata)
    nodes = table(
        "nodes",
        column("record_id", metadata.tables["kb.pdf_record_native"].c.record_id.type),
        column("native_address", access.c.pointer.type),
    ).alias("n")
    statement = (
        select(nodes.c.record_id, array([selected.c.ordinal]).label("path"))
        .join(selected, nodes.c.native_address == selected.c.pointer)
        .add_cte(access, subtree, selected, ancestors)
    )
    rendered = str(
        statement.compile(
            dialect=dialect(paramstyle="named"), compile_kwargs={"literal_binds": True}
        )
    )
    (parsed,) = parse_sql(rendered)
    if (
        not isinstance(parsed.stmt, ast.SelectStmt)
        or parsed.stmt.withClause is None
        or parsed.stmt.withClause.ctes is None
    ):
        raise ValueError("selected membership requires a recursive query")
    ctes = ",".join(RawStream()(item) for item in parsed.stmt.withClause.ctes)
    parsed.stmt.withClause = None
    roots = RawStream()(parsed.stmt)
    # The containment relation is supplied by the native event composition below.
    contained = table("contained", column("record_id", nodes.c.record_id.type))
    predicate = nodes.c.record_id.in_(select(contained.c.record_id))
    return (
        ctes,
        roots,
        str(
            predicate.compile(
                dialect=dialect(paramstyle="named"), compile_kwargs={"literal_binds": True}
            )
        ),
    )


def selected_source_reader_sql(*, target_metadata: MetaData | None = None) -> str:
    if target_metadata is None:
        from .metadata import metadata

        target_metadata = metadata
    membership_ctes, roots, node_filter = _selected_membership_sql(target_metadata)
    ctes = pdf_native_event_ctes(
        published_sql="SELECT * FROM ops.read_pdf_published_revision(p_task,p_native_product,p_digest)",
        roots_sql=roots,
        additional_ctes=membership_ctes
        + """, contained(record_id) AS (
 SELECT n.record_id FROM kb.pdf_record_native n JOIN published p
 ON n.product_id=p.build_id AND n.revision_id=p.build_id
 JOIN selected a ON a.pointer=n.native_address
 UNION
 SELECT child.record_id FROM contained parent JOIN kb.pdf_record_native n
 ON n.record_id=parent.record_id JOIN published p
 ON n.product_id=p.build_id AND n.revision_id=p.build_id
 CROSS JOIN LATERAL (
 SELECT f.value->>'target' AS record_id FROM jsonb_each(n.structure_json->'fields') f
 WHERE f.value->>'kind'='object'
 UNION ALL
 SELECT m.record_id FROM kb.pdf_record_membership m
 WHERE m.product_id=p.build_id AND m.revision_id=p.build_id
 AND m.parent_id=n.record_id AND m.value_kind='record'
 ) child
 ), selected_metadata AS MATERIALIZED (
 SELECT c.* FROM kb.pdf_record_companion c JOIN published p
 ON c.product_id=p.build_id AND c.revision_id=p.build_id
 WHERE c.family='native_metadata' AND CASE c.body->>'kind'
 WHEN 'formula_outcomes' THEN c.body->>'pointer' IN (SELECT pointer FROM selected)
 WHEN 'recognition_coverage' THEN
 (ops.pdf_companion_body(c.product_id,c.revision_id,c.family,c.local_id,c.body)
 ->'value'->>'section_pointer') IN
 (SELECT pointer FROM selected UNION SELECT pointer FROM ancestors)
 ELSE false END
 )""",
        node_filter_sql=node_filter,
    )
    metadata_ctes = pdf_companion_event_ctes(
        companions_sql="SELECT * FROM selected_metadata",
        prefix="metadata_",
    )
    ctes += "," + metadata_ctes
    sql = (
        """
CREATE OR REPLACE FUNCTION ops.read_pdf_selected_source_events(
 p_project text,p_demand text,p_read text,p_use text,p_product text,p_derivation text,
 p_section text,p_membership text,p_policy text)
RETURNS SETOF jsonb LANGUAGE plpgsql VOLATILE SECURITY DEFINER
SET search_path=pg_catalog,pg_temp AS $selected$
DECLARE revision ops.pdf_published_revision; p_task bigint; p_native_product text; p_digest text;
BEGIN
 IF p_section IS NULL OR p_membership IS DISTINCT FROM 'descendants'
 OR p_policy IS DISTINCT FROM 'section-source-context-v1' THEN
 RAISE EXCEPTION 'invalid selected source selector/policy' USING ERRCODE='22023'; END IF;
 SELECT * INTO STRICT revision FROM ops.require_published_companion_pin(
 p_project,p_demand,p_read,p_use,p_product,p_derivation);
 p_task:=revision.task_id; p_native_product:=revision.product_key; p_digest:=revision.logical_digest;
 IF NOT EXISTS(SELECT FROM kb.pdf_record_access a WHERE a.product_id=revision.build_id
 AND a.revision_id=revision.build_id AND a.pointer=p_section
 AND a.label IN ('section','chapter')) THEN
 RAISE EXCEPTION 'selected source root is not a published section' USING ERRCODE='22023'; END IF;
 RETURN QUERY
"""
        + ctes
        + """,
 companion AS MATERIALIZED (
 SELECT c.family,c.local_id,c.ordinal,c.body::text AS payload
 FROM ops.pdf_record_context_rows(p_task,p_native_product,p_digest,
 ARRAY(SELECT pointer FROM selected),p_section) c
 UNION ALL SELECT c.family,c.local_id,c.ordinal,
 c.body::text
 FROM kb.pdf_record_companion c JOIN published p
 ON c.product_id=p.build_id AND c.revision_id=p.build_id
 WHERE c.family='health'
 UNION ALL SELECT c.family,c.local_id,c.ordinal,c.body::text FROM selected_metadata c
 UNION ALL SELECT 'endpoint',e.relation_id||':'||e.ordinal::text,e.ordinal,
 jsonb_build_object('relation_id',e.relation_id,'endpoint_ordinal',e.ordinal,'role',e.role,
 'target_task_id',CASE WHEN e.target_task_id=0 THEN p_task ELSE e.target_task_id END,
 'target_product_key',CASE WHEN e.target_task_id=0 THEN p_native_product ELSE e.target_product_key END,
 'target_content_digest',CASE WHEN e.target_task_id=0
 THEN p_digest ELSE e.target_content_digest END,
 'occurrence_id',e.occurrence_id)::text
 FROM kb.pdf_record_endpoint e JOIN published p
 ON e.product_id=p.build_id AND e.revision_id=p.build_id
 WHERE e.relation_id IN (SELECT c.local_id FROM ops.pdf_record_context_rows(
 p_task,p_native_product,p_digest,ARRAY(SELECT pointer FROM selected),p_section) c
 WHERE c.family='relation')
 ), companion_order AS (
 SELECT *,row_number() OVER(ORDER BY family COLLATE "C",ordinal,local_id COLLATE "C") AS position
 FROM companion
 ), external AS (
 SELECT jsonb_build_object('from_pointer',a.pointer,'field',r.field_name,
 'reference_id',r.reference_id,'source_id',r.source_id,'native_address',origin.native_address,
 'source_ordinal',a.ordinal,'source_order',to_jsonb(w.path),
 'target',jsonb_build_object('task_id',p_task,'product_key',p_native_product,'content_digest',p_digest)||
 CASE WHEN r.field_name IN ('source_cell_id','target_cell_id')
 THEN jsonb_build_object('address_space','native_graph_cell','cell_id_lexical',r.native_pointer)
 ELSE jsonb_build_object('address_space','native_item','pointer',r.native_pointer) END,
 'resolution','qualified_external') AS body
 FROM selected a JOIN walk w ON w.path[1]=a.ordinal
 JOIN kb.pdf_record_reference r ON r.source_id=w.record_id
 JOIN nodes origin ON origin.record_id=r.source_id
 JOIN published p ON r.product_id=p.build_id AND r.revision_id=p.build_id
 WHERE r.native_pointer IS NOT NULL AND NOT EXISTS(SELECT FROM nodes target
 WHERE target.record_id=r.target_id)
 UNION ALL
 SELECT jsonb_build_object('relation_id',e.relation_id,'endpoint_ordinal',e.ordinal,
 'role',e.role,'target',jsonb_build_object('task_id',CASE WHEN e.target_task_id=0
 THEN p_task ELSE e.target_task_id END,
 'product_key',CASE WHEN e.target_task_id=0 THEN p_native_product ELSE e.target_product_key END,
 'content_digest',CASE WHEN e.target_task_id=0 THEN p_digest ELSE e.target_content_digest END,
 'occurrence_id',e.occurrence_id),'resolution','qualified_external')
 FROM kb.pdf_record_endpoint e JOIN published p
 ON e.product_id=p.build_id AND e.revision_id=p.build_id
 WHERE e.relation_id IN (SELECT local_id FROM companion WHERE family='relation')
 AND NOT ((e.target_task_id,e.target_product_key,e.target_content_digest) IN
 ((p_task,p_native_product,p_digest),(0::bigint,'@self','@self'))
 AND e.occurrence_id IN (SELECT local_id FROM companion WHERE family='occurrence'))
 ), output(phase,path,event) AS (
 SELECT -1,ARRAY[]::bigint[],jsonb_build_object('event','selection_metadata',
 'selected_count',(SELECT count(*) FROM selected),
 'membership_sha256',(SELECT encode(sha256(convert_to(COALESCE(
 string_agg(pointer||chr(9)||ordinal::text||chr(9)||COALESCE(parent_pointer,'')||chr(10),''
 ORDER BY ordinal),'') ,'UTF8')),'hex') FROM selected))
 UNION ALL
 SELECT 0,ARRAY[a.ordinal,-1]::bigint[],jsonb_build_object('event','record_start',
 'pointer',a.pointer,'record_id',n.record_id,'ordinal',a.ordinal,'parent_pointer',a.parent_pointer,
 'section_pointer',a.section_pointer,'label',a.label,'role','selected')
 FROM selected a JOIN nodes n ON n.native_address=a.pointer
 UNION ALL
 SELECT 0,path,jsonb_build_object('event','native_fragment','native',
 jsonb_build_object('kind',kind,'value',value,'prefix',prefix)) FROM events
 UNION ALL
 SELECT 0,ARRAY[ordinal,3]::bigint[],jsonb_build_object('event','record_end','pointer',pointer)
 FROM selected
 UNION ALL
 SELECT 1,ARRAY[ordinal]::bigint[],jsonb_build_object('event','context','kind','ancestor',
 'pointer',pointer,'ordinal',ordinal,'parent_pointer',parent_pointer,'label',label,
 'name',native_json->'name') FROM access WHERE pointer IN (SELECT pointer FROM ancestors)
 UNION ALL
 SELECT 2,ARRAY[row_number() OVER(ORDER BY r.pointer,r.region_index)]::bigint[],
 jsonb_build_object('event','context','kind','frame','body',to_jsonb(r)-'product_id'-'revision_id')
 FROM kb.pdf_record_region r JOIN published p
 ON r.product_id=p.build_id AND r.revision_id=p.build_id
 WHERE r.pointer IN (SELECT pointer FROM selected)
 UNION ALL
 SELECT 3,ARRAY[position,0]::bigint[],jsonb_build_object('event',
 CASE WHEN family='native_metadata' THEN 'companion_native_start' ELSE 'companion_start' END,
 'family',family,'local_id',local_id,'ordinal',ordinal) FROM companion_order
 UNION ALL
 SELECT 3,ARRAY[c.position,1,part]::bigint[],jsonb_build_object('event','scalar_part',
 'part',part,'encoding','base64','value',encode(substring(convert_to(c.payload,'UTF8')
 FROM (part*32768+1)::integer FOR 32768),'base64'),'final',
 (part+1)*32768>=octet_length(c.payload)) FROM companion_order c
 CROSS JOIN LATERAL generate_series(0,(octet_length(c.payload)-1)/32768) part
 WHERE c.family<>'native_metadata'
 UNION ALL
 SELECT 3,ARRAY[position,2]::bigint[],jsonb_build_object('event','companion_end',
 'byte_length',octet_length(payload),'sha256',encode(sha256(convert_to(payload,'UTF8')),'hex'))
 FROM companion_order WHERE family<>'native_metadata'
 UNION ALL
 SELECT 3,ARRAY[c.position,1,row_number() OVER(PARTITION BY c.position
 ORDER BY e.phase,e.field_name COLLATE "C",e.subphase,e.part_ordinal)]::bigint[],
 jsonb_build_object('event','companion_native_fragment','fragment',e.event)
 FROM metadata_events e JOIN companion_order c ON c.family='native_metadata'
 AND c.local_id=e.local_id
 UNION ALL
 SELECT 3,ARRAY[position,2]::bigint[],jsonb_build_object('event','companion_native_end')
 FROM companion_order WHERE family='native_metadata'
 UNION ALL
 SELECT 4,ARRAY[row_number() OVER(ORDER BY body::text)]::bigint[],
 jsonb_build_object('event','outside_reference','body',body) FROM external
 ) SELECT event FROM output ORDER BY phase,path;
END $selected$;
REVOKE ALL ON FUNCTION ops.read_pdf_selected_source_events(
 text,text,text,text,text,text,text,text,text) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION ops.read_pdf_selected_source_events(
 text,text,text,text,text,text,text,text,text)
 TO corpus_sem_reader,corpus_sem_writer,corpus_sem_evaluator;
"""
    )

    declaration = yaml.safe_load(
        files("corpus_structure").joinpath("model/semantic/selected-source.yaml").read_bytes()
    )
    profile = json.loads(declaration["annotations"]["selected-source"])
    memberships = declaration["enums"]["SourceMembership"]["permissible_values"]
    if len(memberships) != 1:
        raise ValueError("selected source native authoring requires one membership policy")
    membership = next(iter(memberships))

    def quote(value):
        return "'" + str(value).replace("'", "''") + "'"

    return (
        sql.replace("'descendants'", quote(membership))
        .replace("'section-source-context-v1'", quote(profile["context_policy"]))
        .replace("32768", str(profile["part_bytes"]))
    )
