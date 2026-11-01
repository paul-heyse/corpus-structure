"""Forward authoring of model-derived, protected typed companion projections."""

from __future__ import annotations

from sqlalchemy import literal_column, select
from sqlalchemy.dialects.postgresql import dialect

from .companion_projection import FAMILIES, projection
from .native_objects import definition_from_sql

PARAMETERS = "p_project text,p_run bigint,p_release text,p_task bigint,p_product text,p_digest text"
SIGNATURE_TYPES = "text,bigint,text,bigint,text,text"


def pin_guard_sql() -> str:
    from .pdf_storage import selected_native_ancestry

    ancestry = selected_native_ancestry(literal_column("p_run"))
    query = select(ancestry.c.task_id).where(
        ancestry.c.task_id == literal_column("p_task"),
        ancestry.c.product_key == literal_column("p_product"),
        ancestry.c.content_digest == literal_column("p_digest"),
    )
    membership = str(
        query.compile(dialect=dialect(paramstyle="named"), compile_kwargs={"literal_binds": True})
    )
    return f"""CREATE OR REPLACE FUNCTION ops.require_published_companion_pin({PARAMETERS})
RETURNS ops.pdf_published_revision LANGUAGE plpgsql STABLE SECURITY DEFINER
SET search_path=pg_catalog,pg_temp AS $pin$
DECLARE published ops.pdf_published_revision; origin_run bigint;
BEGIN
 PERFORM data.require_runtime_principal('read');
 IF p_project IS NULL OR p_run IS NULL OR p_release IS NULL OR p_task IS NULL
 OR p_product IS NULL OR p_digest IS NULL OR NOT EXISTS(
 SELECT FROM ops.run r WHERE r.id=p_run AND r.project_id=p_project AND r.release_id=p_release) THEN
 RAISE EXCEPTION 'published source run/project/release pin is unavailable'
 USING ERRCODE='22023'; END IF;
 PERFORM sem.require_execution_operation(p_release,'read_native_source');
 SELECT p.* INTO published FROM ops.read_pdf_published_revision(p_task,p_product,p_digest) p;
 IF NOT FOUND OR published.release_id IS DISTINCT FROM p_release THEN
 RAISE EXCEPTION 'published source pin is unavailable or staged' USING ERRCODE='22023'; END IF;
 SELECT t.run_id INTO origin_run FROM ops.task t JOIN ops.run r ON r.id=t.run_id
 WHERE t.id=p_task AND r.project_id=p_project;
 IF NOT FOUND THEN
 RAISE EXCEPTION 'published source is unavailable in this project' USING ERRCODE='22023'; END IF;
 IF origin_run<>p_run AND NOT EXISTS({membership}) THEN
 RAISE EXCEPTION 'published source is outside selected run ancestry' USING ERRCODE='22023'; END IF;
 RETURN published;
END $pin$;
"""


def family_sql(family: str) -> str:
    selected = projection(family)
    pg = dialect(paramstyle="named")
    quote = pg.identifier_preparer.quote
    returns = ",".join(quote(c.name) + " " + c.type.compile(dialect=pg) for c in selected.columns)
    expressions = ",".join(
        "CAST(" + expression + " AS " + column.type.compile(dialect=pg) + ")"
        for column, expression in zip(selected.columns, selected.expressions, strict=True)
    )
    join = ""
    if family == "relation":
        join = (
            "JOIN kb.pdf_record_endpoint e ON e.product_id=c.product_id "
            "AND e.revision_id=c.revision_id AND e.relation_id=c.local_id"
        )
    elif family == "mapping_report":
        join = "JOIN companions i ON i.family='input' AND i.local_id=c.body->>'input_index'"
    return f"""CREATE OR REPLACE FUNCTION {selected.function_name}({PARAMETERS})
RETURNS TABLE({returns}) LANGUAGE plpgsql STABLE SECURITY DEFINER
SET search_path=pg_catalog,pg_temp AS $projection$
DECLARE published ops.pdf_published_revision;
BEGIN
 published:=ops.require_published_companion_pin(p_project,p_run,p_release,p_task,p_product,p_digest);
 RETURN QUERY WITH companions AS MATERIALIZED (
 SELECT c.product_id,c.revision_id,c.family,c.local_id,c.ordinal,
 ops.pdf_companion_body(c.product_id,c.revision_id,c.family,c.local_id,c.body) AS body
 FROM kb.pdf_record_companion c
 WHERE c.product_id=published.build_id AND c.revision_id=published.build_id
 AND c.family IN ('{family}'{",'input'" if family == "mapping_report" else ""})
 ) SELECT {expressions} FROM companions c {join} WHERE c.family='{family}';
END $projection$;
"""


def companion_projection_definitions(connection):
    """Complete source definitions consumed by native autogeneration/admission.

    The helper is private to the publisher's protected functions. Reader grants belong
    only to the four modeled projections, never to the underlying native relations.
    """
    sources = (("pin", pin_guard_sql()), *((family, family_sql(family)) for family in FAMILIES))
    return tuple(
        definition_from_sql(
            connection,
            sql,
            source="companion-projections:" + name,
            owner="corpus_sem_publisher",
            grants=()
            if name == "pin"
            else tuple(
                (role, "EXECUTE", False)
                for role in ("corpus_sem_reader", "corpus_sem_writer", "corpus_sem_evaluator")
            ),
        )
        for name, sql in sources
    )
