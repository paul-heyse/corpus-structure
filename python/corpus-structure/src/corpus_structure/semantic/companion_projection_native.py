"""Forward authoring of model-derived, protected typed companion projections."""

from __future__ import annotations

from pglast import ast, enums
from pglast.stream import RawStream
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
    return f"""CREATE OR REPLACE FUNCTION ops.require_published_companion_pin({parameters_sql()})
RETURNS ops.pdf_published_revision LANGUAGE plpgsql VOLATILE SECURITY DEFINER
SET search_path=pg_catalog,pg_temp AS $pin$
DECLARE published ops.pdf_published_revision; boundary ops.data_demand_read; receipt jsonb;
BEGIN
 PERFORM data.require_runtime_principal('read');
 IF NOT EXISTS(SELECT FROM ops.data_demand d WHERE d.id=p_demand AND d.project_id=p_project) THEN
 RAISE EXCEPTION 'published source demand/project differs' USING ERRCODE='22023'; END IF;
 PERFORM ops.ddo_require_selected_output(p_demand,p_read,p_use,p_product,p_derivation);
 SELECT * INTO STRICT boundary FROM ops.data_demand_read WHERE id=p_read AND demand_id=p_demand;
 receipt:=ops.ddo_pdf_derivation_receipt(p_project,p_product,p_derivation,NULL,boundary);
 SELECT revision.* INTO STRICT published FROM ops.pdf_published_revision revision
 WHERE revision.build_id=receipt->'publication'->>'build_id'
 AND revision.task_id=(receipt->'publication'->>'task_id')::bigint
 AND revision.product_key=receipt->'publication'->>'product_key'
 AND revision.logical_digest=receipt->'publication'->>'logical_digest';
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
        arguments.extend(("published.build_id", "published.release_id", "published.task_id", "published.product_key", "published.logical_digest", "selected_release"))
        body = "SELECT * FROM " + selected.function_name + "_rows(" + ",".join(arguments) + ")"
    else:
        body = str(
            native_statement(selected.body_statement, selected.recipe).compile(
                dialect=pg, compile_kwargs={"literal_binds": True}
            )
        )
    return f"""CREATE OR REPLACE FUNCTION {selected.function_name}({parameters_sql()})
RETURNS TABLE({returns}) LANGUAGE plpgsql VOLATILE SECURITY DEFINER
SET search_path=pg_catalog,pg_temp AS $projection$
DECLARE published ops.pdf_published_revision; selected_release text;
BEGIN
 published:=ops.require_published_companion_pin(p_project,p_demand,p_read,p_use,p_product,p_derivation);
 SELECT release_id INTO STRICT selected_release FROM ops.data_demand WHERE id=p_demand;
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
            argType=ast.TypeName(names=(ast.String(sval=typ),)),
            mode=enums.FunctionParameterMode.FUNC_PARAM_IN,
        )
        for name, typ in (("p_build", "text"), ("p_producer_release", "text"), ("p_native_task", "bigint"), ("p_native_product", "text"), ("p_native_digest", "text"), ("p_selection_release", "text"))
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
                "_published_task_id": "p_native_task",
                "_published_product_key": "p_native_product",
                "_published_content_digest": "p_native_digest",
                "_selection_release_id": "p_selection_release",
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
