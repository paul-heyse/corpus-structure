"""Forward native realization of the model-owned PDF companion contract."""

from pathlib import Path


def observation_publication_sql(context=None, *, target_metadata=None) -> str:
    """Render the current observation-only publication kernel from its owned source."""
    from pglast import ast
    from pglast.stream import RawStream

    from .native_shapes import decomposed_record_guards
    from .pdf_contracts import trusted_pdf_context
    from .pdf_observations import PdfObservationPageReport
    from .prepared_sql import prepare_sql

    context = trusted_pdf_context() if context is None else context
    source = Path(__file__).with_name("sql").joinpath("pdf_observation.sql")
    functions = {
        tuple(part.sval for part in raw.stmt.funcname or ()): raw.stmt
        for raw in prepare_sql(source.read_text(), source=str(source)).private_tree()
        if isinstance(raw.stmt, ast.CreateFunctionStmt)
    }
    functions.update(observation_value_declarations(context, target_metadata=target_metadata))
    declaration = functions["ops", "publish_pdf_observation"]
    meaning = functions["ops", "pdf_observation_meaning"]
    projection = functions["ops", "pdf_observation_projection_for_request"]
    projection_option = next(
        option for option in projection.options or () if option.defname == "as"
    )
    marker = "-- {observation_report_shape}"
    if projection_option.arg[0].sval.count(marker) != 1:
        raise ValueError("observation report requires its one typed boundary")
    from pydantic import TypeAdapter

    from .identity import canonical_bytes

    report_schema = TypeAdapter(PdfObservationPageReport).json_schema(
        ref_template="#/definitions/{model}"
    )
    if "$defs" in report_schema:
        report_schema["definitions"] = report_schema.pop("$defs")
    literal = canonical_bytes(report_schema).decode().replace("'", "''")
    projection_option.arg[0].sval = projection_option.arg[0].sval.replace(
        marker,
        "IF NOT coalesce(public.json_matches_schema('"
        + literal
        + "'::json,report::json),false) THEN "
        "RAISE EXCEPTION 'observation report violates its finite manifest contract' USING ERRCODE='23514'; END IF;",
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
        + ";\nALTER FUNCTION ops.pdf_observation_projection_for_request(jsonb,bigint,bigint,text,ops.data_request) OWNER TO corpus_sem_publisher;\n"
        + "REVOKE ALL ON FUNCTION ops.pdf_observation_projection_for_request(jsonb,bigint,bigint,text,ops.data_request) FROM PUBLIC;\n"
        + RawStream()(functions["ops", "pdf_observation_projection"])
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


def observation_value_declarations(context, *, target_metadata=None):
    """Generate meaning, policy lookup and the current-request projection envelope."""
    from pglast import ast, parse_sql
    from sqlalchemy import BigInteger, Text, cast, column, func, or_, select
    from sqlalchemy.dialects.postgresql import JSONB, array

    from .metadata import metadata
    from .native_program import (
        Block,
        If,
        Local,
        Parameter,
        Perform,
        Raise,
        Return,
        SelectInto,
        core_variable,
        function,
        pg_type,
    )
    from .pdf_observations import (
        MEANING_SPEC,
        PROFILE_CONTRACT,
        PROFILE_REFERENCE,
        PROFILE_ROLE,
        observation_meaning_program,
    )

    model = metadata if target_metadata is None else target_metadata
    task = model.tables["ops.task"]
    request = model.tables["ops.data_request"]
    definition = model.tables["sem.data_operation_definition"]
    inputs = model.tables["sem.input"]
    p_release = core_variable("p_release", Text())
    p_definition_release = core_variable("p_definition", definition.c.release_id.type, "release_id")
    support = core_variable("p_definition", JSONB(), "support_contract")
    asset, profile = (core_variable(name, JSONB()) for name in ("asset", "profile"))
    assets = func.jsonb_array_elements(support["assets"]).table_valued(column("value", JSONB()))
    policy = function(
        "ops",
        "pdf_recognition_profile",
        parameters=(
            Parameter("p_release", pg_type("text")),
            Parameter("p_definition", pg_type("sem", "data_operation_definition")),
        ),
        returns=pg_type("jsonb"),
        volatility="stable",
        search_path=("pg_catalog", "pg_temp"),
        body=Block(
            (
                If(
                    p_definition_release.is_distinct_from(p_release),
                    (Raise("recognition policy belongs to another release", "23514"),),
                ),
                SelectInto(
                    select(assets.c.value).where(
                        assets.c.value["reference"].astext == PROFILE_REFERENCE,
                        assets.c.value["contract"].astext == PROFILE_CONTRACT,
                        assets.c.value["role"].astext == PROFILE_ROLE,
                    ),
                    ("asset",),
                    True,
                ),
                SelectInto(
                    select(cast(func.convert_from(inputs.c.content, "UTF8"), JSONB())).where(
                        inputs.c.release_id == p_release,
                        inputs.c.input_kind == "dependency",
                        inputs.c.input_name
                        == ("data-operations/contracts/" + asset["contract"].astext),
                        inputs.c.content_digest == asset["content_digest"].astext,
                        func.encode(func.sha256(inputs.c.content), "hex")
                        == inputs.c.content_digest,
                    ),
                    ("profile",),
                    True,
                ),
                Perform(
                    func.ops.ddo_fields(
                        profile,
                        array(
                            [
                                "version",
                                "base_recipe_digest",
                                "recipes",
                                "recovery_policy",
                                "source_recovery",
                            ],
                            type_=Text(),
                        ),
                    )
                ),
                If(
                    profile["version"].astext.is_distinct_from("pdf-recognition-profile-1"),
                    (Raise("unsupported recognition policy", "23514"),),
                ),
                Return(profile),
            ),
            (Local("asset", pg_type("jsonb")), Local("profile", pg_type("jsonb"))),
        ),
    )
    parameters = (
        Parameter("p_receipt", pg_type("jsonb")),
        Parameter("p_task", pg_type("bigint")),
        Parameter("p_attempt", pg_type("bigint")),
        Parameter("p_holder", pg_type("text")),
    )
    job_request = core_variable("job", task.c.data_request_id.type, "data_request_id")
    conditions = tuple(
        core_variable("request", request.c[left].type, left).is_distinct_from(
            core_variable("job", task.c[right].type, right)
        )
        for left, right in (
            ("live_task_id", "id"),
            ("generation", "data_generation"),
            ("release_id", "release_id"),
        )
    )
    envelope = function(
        "ops",
        "pdf_observation_projection",
        parameters=parameters,
        returns=pg_type("jsonb"),
        volatility="stable",
        security_definer=True,
        search_path=("pg_catalog", "pg_temp"),
        body=Block(
            (
                SelectInto(
                    select(task).where(task.c.id == core_variable("p_task", BigInteger())),
                    ("job",),
                    True,
                ),
                SelectInto(select(request).where(request.c.id == job_request), ("request",), True),
                If(
                    or_(*conditions),
                    (
                        Raise(
                            "active observation projection requires its current task request basis",
                            "23514",
                        ),
                    ),
                ),
                Return(
                    func.ops.pdf_observation_projection_for_request(
                        core_variable("p_receipt", JSONB()),
                        core_variable("p_task", BigInteger()),
                        core_variable("p_attempt", BigInteger()),
                        core_variable("p_holder", Text()),
                        core_variable("request", JSONB()),
                    )
                ),
            ),
            (Local("job", task), Local("request", request)),
        ),
    )
    specification = next(
        source.content for source in context.domain.sources if source.name == MEANING_SPEC
    )
    meaning = function(
        "ops",
        "pdf_observation_meaning",
        parameters=(Parameter("p_payload", pg_type("bytea")),),
        returns=pg_type("jsonb"),
        body=observation_meaning_program(specification),
        volatility="immutable",
        strict=True,
        search_path=("pg_catalog", "pg_temp"),
    )
    return {
        tuple(part.sval for part in declaration.stmt.funcname or ()): declaration.stmt
        for declaration in parse_sql(meaning + ";" + policy + ";" + envelope)
        if isinstance(declaration.stmt, ast.CreateFunctionStmt)
    }
