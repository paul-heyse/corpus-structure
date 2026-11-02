"""Forward native realization of the model-owned PDF companion contract."""

from pathlib import Path


def observation_publication_sql(context=None) -> str:
    """The retained bundle kernel, narrowed to recognition observations at entry.

    The shared source remains the single maintained algorithm. The old generic
    document entry point is frozen history, not a current write capability.
    """
    from pglast import ast
    from pglast.stream import RawStream

    from .native_shapes import decomposed_record_guards
    from .pdf_contracts import trusted_pdf_context
    from .prepared_sql import prepare_sql

    context = trusted_pdf_context() if context is None else context
    source = Path(__file__).with_name("sql").joinpath("pdf_integrated.sql")
    declaration = next(
        raw.stmt
        for raw in prepare_sql(source.read_text(), source=str(source)).private_tree()
        if isinstance(raw.stmt, ast.CreateFunctionStmt)
        and tuple(part.sval for part in raw.stmt.funcname or ())
        == ("ops", "publish_integrated_pdf")
    )
    declaration.funcname = tuple(
        ast.String(sval=part) for part in ("ops", "publish_pdf_observation")
    )
    option = next(option for option in declaration.options or () if option.defname == "as")
    body = option.arg[0].sval
    parse = " wire:=convert_from(p_payload,'UTF8')::json;\n"
    if body.count(parse) != 1 or body.count("BEGIN\n") != 1:
        raise ValueError("observation bundle entry requires one declared payload parse")
    body = body.replace(parse, "", 1).replace(
        "BEGIN\n",
        """BEGIN
 wire:=convert_from(p_payload,'UTF8')::json;
 IF json_typeof(wire) IS DISTINCT FROM 'object' OR
 wire->>'kind' IS DISTINCT FROM 'recognition_observation' THEN
 RAISE EXCEPTION 'recognition observation product required' USING ERRCODE='23514'; END IF;
""",
        1,
    )
    operation = "sem.require_execution_operation(run.release_id,'publish_integrated_pdf')"
    if body.count(operation) != 1:
        raise ValueError("observation bundle requires its declared operation fence")
    body = body.replace(
        operation, "sem.require_execution_operation(run.release_id,'publish_pdf_observation')"
    )
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
    body = body.replace(
        "-- {selected_content_guard}",
        "RAISE EXCEPTION 'document content is not an observation' USING ERRCODE='23514';",
    )
    option.arg[0].sval = body
    signature = "ops.publish_pdf_observation(bigint,bigint,text,text,bytea,bytea[])"
    return (
        RawStream()(declaration)
        + ";\nALTER FUNCTION "
        + signature
        + " OWNER TO corpus_sem_publisher;\nREVOKE ALL ON FUNCTION "
        + signature
        + " FROM PUBLIC;\nGRANT EXECUTE ON FUNCTION "
        + signature
        + " TO corpus_sem_writer;\n"
    )
