"""Forward authoring of model-derived, protected typed companion projections."""

from __future__ import annotations

from pglast import ast, enums
from pglast.stream import RawStream
from sqlalchemy import literal_column, select
from sqlalchemy.dialects.postgresql import dialect

from .companion_projection import FAMILIES, projection
from .native_objects import definition_from_sql
from .native_sql_body import sql_standard_definition
from .prepared_sql import prepare_sql
from .projection_recipe import native_statement


def parameters_sql() -> str:
    pg = dialect(paramstyle="named")
    return ",".join(
        p.native_name + " " + p.sql_type.compile(dialect=pg)
        for p in projection(FAMILIES[0]).recipe.parameters
    )


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
    return f"""CREATE OR REPLACE FUNCTION ops.require_published_companion_pin({parameters_sql()})
RETURNS ops.pdf_published_revision LANGUAGE plpgsql STABLE SECURITY DEFINER
SET search_path=pg_catalog,pg_temp AS $pin$
DECLARE published ops.pdf_published_revision; origin_run bigint;
BEGIN
 PERFORM data.require_runtime_principal('read');
 IF p_project IS NULL OR p_run IS NULL OR p_selection_release IS NULL OR p_task IS NULL
 OR p_product IS NULL OR p_digest IS NULL OR NOT EXISTS(
 SELECT FROM ops.run r WHERE r.id=p_run AND r.project_id=p_project
 AND r.release_id=p_selection_release) THEN
 RAISE EXCEPTION 'published source run/project/release pin is unavailable'
 USING ERRCODE='22023'; END IF;
 PERFORM sem.require_execution_operation(p_selection_release,'read_native_source');
 SELECT p.* INTO published FROM ops.read_pdf_published_revision(p_task,p_product,p_digest) p;
 IF NOT FOUND OR published.release_id IS NULL THEN
 RAISE EXCEPTION 'published source pin is unavailable or staged' USING ERRCODE='22023'; END IF;
 PERFORM sem.require_execution_operation(published.release_id,'read_native_source');
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
    if family == "input":
        arguments = [p.native_name for p in selected.recipe.parameters]
        arguments.extend(("published.build_id", "published.release_id"))
        body = "SELECT * FROM " + selected.function_name + "_rows(" + ",".join(arguments) + ")"
    else:
        body = str(
            native_statement(selected.body_statement, selected.recipe).compile(
                dialect=pg, compile_kwargs={"literal_binds": True}
            )
        )
    return f"""CREATE OR REPLACE FUNCTION {selected.function_name}({parameters_sql()})
RETURNS TABLE({returns}) LANGUAGE plpgsql STABLE SECURITY DEFINER
SET search_path=pg_catalog,pg_temp AS $projection$
DECLARE published ops.pdf_published_revision;
BEGIN
 published:=ops.require_published_companion_pin(p_project,p_run,p_selection_release,p_task,p_product,p_digest);
 RETURN QUERY {body};
END $projection$;
"""


def input_body_definition(connection):
    """Private pure SELECT; the public wrapper retains its mandatory guard sequence."""
    selected = projection("input")
    envelope = (
        prepare_sql(family_sql("input"), source="input projection envelope").private_tree()[0].stmt
    )
    if not isinstance(envelope, ast.CreateFunctionStmt):
        raise TypeError("input projection requires a function envelope")
    envelope.funcname = tuple(
        ast.String(sval=part) for part in (selected.function_name + "_rows").split(".")
    )
    inputs = tuple(
        p
        for p in envelope.parameters or ()
        if p.mode != enums.FunctionParameterMode.FUNC_PARAM_TABLE
    )
    outputs = tuple(
        p
        for p in envelope.parameters or ()
        if p.mode == enums.FunctionParameterMode.FUNC_PARAM_TABLE
    )
    internal = tuple(
        ast.FunctionParameter(
            name=name,
            argType=ast.TypeName(names=(ast.String(sval="text"),)),
            mode=enums.FunctionParameterMode.FUNC_PARAM_IN,
        )
        for name in ("p_build", "p_producer_release")
    )
    envelope.parameters = (*inputs, *internal, *outputs)
    # This helper is not a second public authorization surface.
    for option in envelope.options or ():
        if option.defname == "security":
            option.arg = ast.Boolean(boolval=False)
    definition = definition_from_sql(
        connection,
        RawStream()(envelope),
        source="companion-input:private-body",
        owner="corpus_sem_publisher",
        grants=(),
    )
    return sql_standard_definition(
        definition,
        native_statement(
            selected.body_statement,
            selected.recipe,
            internal_bindings={
                "_published_build_id": "p_build",
                "_published_release_id": "p_producer_release",
            },
        ),
    )


def companion_projection_definitions(connection):
    """Complete source definitions consumed by native autogeneration/admission.

    The helper is private to the publisher's protected functions. Reader grants belong
    only to the four modeled projections, never to the underlying native relations.
    """
    sources = (("pin", pin_guard_sql()), *((family, family_sql(family)) for family in FAMILIES))
    definitions = tuple(
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
    return (definitions[0], input_body_definition(connection), *definitions[1:])
