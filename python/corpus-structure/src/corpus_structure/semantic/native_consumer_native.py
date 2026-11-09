"""Forward deployment of bounded derivations and native consumer custody."""

from pathlib import Path


def predicate_interpretation_recipe_sql() -> str:
    """Lower the shared exact release input lookup into a private native function."""
    from sqlalchemy import cast, func, literal_column, select
    from sqlalchemy.dialects.postgresql import JSONB, dialect

    from .metadata import table

    release_input = table("sem.input")
    statement = select(cast(func.convert_from(release_input.c.content, "UTF8"), JSONB)).where(
        release_input.c.release_id
        == literal_column("p_release", type_=release_input.c.release_id.type),
        release_input.c.input_kind == "dependency",
        release_input.c.input_name
        == "execution/implementation/operations/predicate-interpretation.json",
    )
    body = statement.compile(
        dialect=dialect(paramstyle="named"), compile_kwargs={"literal_binds": True}
    )
    return f"""
CREATE OR REPLACE FUNCTION ops.predicate_interpretation_recipe(p_release text)
RETURNS jsonb LANGUAGE sql STABLE SECURITY INVOKER SET search_path=pg_catalog,pg_temp
BEGIN ATOMIC {body}; END;
REVOKE ALL ON FUNCTION ops.predicate_interpretation_recipe(text) FROM PUBLIC;
"""


def native_task_completion_sql(context=None) -> str:
    """One rendered completion source for normal products and native authoring."""
    from .native_shapes import record_shape_guards
    from .ordered_witness_native import ordered_formula_witness_sql
    from .pdf_contracts import trusted_pdf_context

    context = trusted_pdf_context() if context is None else context
    sql = Path(__file__).with_name("sql")
    completion = (
        sql.joinpath("native_task_completion.sql")
        .read_text()
        .replace(
            "-- {native_input_shape_guard}",
            record_shape_guards(context.boundary, "PdfNativeObservationInput", "native_input"),
        )
        .replace(
            "-- {source_record_guard}", sql.joinpath("source_record_completion.sql").read_text()
        )
    )
    return (
        predicate_interpretation_recipe_sql()
        + sql.joinpath("source_record_recognition.sql").read_text()
        + sql.joinpath("source_anchor_coordinates.sql").read_text()
        + sql.joinpath("source_record_coordinates.sql").read_text()
        + ordered_formula_witness_sql()
        + sql.joinpath("source_contributions.sql").read_text()
        + sql.joinpath("source_record_report.sql").read_text()
        + sql.joinpath("dossier_contributions.sql").read_text()
        + sql.joinpath("structural_products.sql").read_text()
        + completion
    )
