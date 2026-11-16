"""Forward native realization of the model-owned PDF companion contract."""

from pathlib import Path


def observation_publication_sql(context=None) -> str:
    """Render the current observation-only publication kernel from its owned source."""
    from pglast import ast
    from pglast.stream import RawStream

    from .native_shapes import decomposed_record_guards
    from .pdf_contracts import trusted_pdf_context
    from .pdf_observations import MEANING_SPEC, PdfObservationPageReport, observation_meaning_sql
    from .prepared_sql import prepare_sql

    context = trusted_pdf_context() if context is None else context
    source = Path(__file__).with_name("sql").joinpath("pdf_observation.sql")
    functions = {
        tuple(part.sval for part in raw.stmt.funcname or ()): raw.stmt
        for raw in prepare_sql(source.read_text(), source=str(source)).private_tree()
        if isinstance(raw.stmt, ast.CreateFunctionStmt)
    }
    declaration = functions["ops", "publish_pdf_observation"]
    meaning = functions["ops", "pdf_observation_meaning"]
    meaning_option = next(option for option in meaning.options or () if option.defname == "as")
    specification = next(source.content for source in context.domain.sources if source.name == MEANING_SPEC)
    marker = "-- {observation_meaning_projection}"
    if meaning_option.arg[0].sval.count(marker) != 1:
        raise ValueError("recognition meaning requires its one captured selection")
    meaning_option.arg[0].sval = meaning_option.arg[0].sval.replace(marker, observation_meaning_sql(specification))
    projection = functions["ops", "pdf_observation_projection"]
    projection_option = next(option for option in projection.options or () if option.defname == "as")
    marker = "-- {observation_report_shape}"
    if projection_option.arg[0].sval.count(marker) != 1:
        raise ValueError("observation report requires its one typed boundary")
    from pydantic import TypeAdapter
    from .identity import canonical_bytes

    report_schema = TypeAdapter(PdfObservationPageReport).json_schema(ref_template="#/definitions/{model}")
    if "$defs" in report_schema:
        report_schema["definitions"] = report_schema.pop("$defs")
    literal = canonical_bytes(report_schema).decode().replace("'", "''")
    projection_option.arg[0].sval = projection_option.arg[0].sval.replace(marker,
        "IF NOT coalesce(public.json_matches_schema('" + literal + "'::json,report::json),false) THEN "
        "RAISE EXCEPTION 'observation report violates its finite manifest contract' USING ERRCODE='23514'; END IF;"
    )
    option = next(option for option in declaration.options or () if option.defname == "as")
    body = option.arg[0].sval
    shapes = decomposed_record_guards(
        context.boundary,
        "PdfObservationProduct",
        "product",
        field_names="envelope_fields",
        collections={
            "inputs": ("input_rows", "input"),
            "occurrences": ("occurrence_rows", "occurrence"),
            "relations": ("relation_rows", "relation"),
            "coverage": ("coverage_rows", "coverage"),
            "mapping_reports": ("mapping_rows", "mapping_report"),
        },
        records={},
    )
    body = body.replace("-- {integrated_shape_guard}", shapes.envelope)
    for name, guard in shapes.rows.items():
        marker = "-- {" + name + "_shape_guard}"
        if body.count(marker) != 1:
            raise ValueError("observation collection needs one declared guard: " + name)
        body = body.replace(marker, guard)
    option.arg[0].sval = body
    signature = "ops.publish_pdf_observation(bigint,bigint,text,text,text,bytea,bytea[])"
    return (
        RawStream()(meaning)
        + ";\nALTER FUNCTION ops.pdf_observation_meaning(bytea) OWNER TO corpus_sem_publisher;\n"
        + "REVOKE ALL ON FUNCTION ops.pdf_observation_meaning(bytea) FROM PUBLIC;\n"
        + RawStream()(functions["ops", "pdf_recognition_profile"])
        + ";\nALTER FUNCTION ops.pdf_recognition_profile(text,sem.data_operation_definition) OWNER TO corpus_sem_publisher;\n"
        + "REVOKE ALL ON FUNCTION ops.pdf_recognition_profile(text,sem.data_operation_definition) FROM PUBLIC;\n"
        + RawStream()(projection)
        + ";\nALTER FUNCTION ops.pdf_observation_projection(jsonb,bigint,bigint,text) OWNER TO corpus_sem_publisher;\n"
        + "REVOKE ALL ON FUNCTION ops.pdf_observation_projection(jsonb,bigint,bigint,text) FROM PUBLIC;\n"
        + "GRANT EXECUTE ON FUNCTION ops.pdf_observation_projection(jsonb,bigint,bigint,text) TO corpus_sem_writer;\n"
        + RawStream()(declaration)
        + ";\nALTER FUNCTION "
        + signature
        + " OWNER TO corpus_sem_publisher;\nREVOKE ALL ON FUNCTION "
        + signature
        + " FROM PUBLIC;\nGRANT EXECUTE ON FUNCTION "
        + signature
        + " TO corpus_sem_writer;\n"
    )
