"""Typed native scoring over the authoritative Core ranking query."""

from typing import Any

from pglast import ast, enums, parse_sql
from pglast.stream import RawStream
from pgvector.sqlalchemy import VECTOR
from sqlalchemy import Integer, Text, and_, cast, column, func, literal, literal_column, or_, select
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, REAL, aggregate_order_by, dialect
from sqlalchemy.types import TypeEngine

from corpus_structure.schema.integrity import role_name

from .native_objects import INTERNAL_PROGRAM, native_privilege_sql
from .native_program import (
    Assign,
    Block,
    ForQuery,
    If,
    Local,
    NativeRoutine,
    Parameter,
    Raise,
    Return,
    ReturnQuery,
    SelectInto,
    core_variable,
    pg_type,
)
from .native_program_registry import ProgramDeclaration


def _query_node(query) -> ast.SelectStmt:
    source = str(
        query.compile(dialect=dialect(paramstyle="named"), compile_kwargs={"literal_binds": True})
    )
    (parsed,) = parse_sql(source)
    if not isinstance(parsed.stmt, ast.SelectStmt):
        raise ValueError("native score expression requires a relational query")
    return parsed.stmt


def _query_array(query, datatype):
    expression = ast.SubLink(
        subLinkType=enums.SubLinkType.ARRAY_SUBLINK, subselect=_query_node(query)
    )
    return literal_column(RawStream()(expression), type_=ARRAY(datatype))


def _text_array_type():
    datatype = pg_type("text")
    datatype.arrayBounds = (ast.Integer(ival=-1),)
    return datatype


def _items(value, *, text=False, ordinal=False):
    source = func.jsonb_array_elements_text(value) if text else func.jsonb_array_elements(value)
    kind: TypeEngine[Any] = Text() if text else JSONB()
    return source.table_valued(
        column("value", kind),
        **({"with_ordinality": "ordinal"} if ordinal else {}),
    ).render_derived("items")


def _field(value, name):
    return func.data.report_field(value, name, type_=JSONB())


def _score_query():
    from .contextual_retrieval import contextual_score_statement

    relation = func.ops.ddo_contextual_vector_rows(
        core_variable("p_inventory", JSONB()), core_variable("p_vectors", JSONB())
    ).table_valued(
        column("inventory_id", Text),
        column("profile_id", Text),
        column("target_id", Text),
        column("vector", VECTOR()),
        column("search_text", Text),
        column("exact_forms", ARRAY(Text)),
    )
    return contextual_score_statement(
        relation,
        inventory_id=core_variable("inventory_key", Text()),
        profile_id=core_variable("profile_key", Text()),
        target_ids=core_variable("target_keys", ARRAY(Text)),
        query_vector=core_variable("query_vector", VECTOR()),
        lexical_query=core_variable("lexical_query", Text()),
        channel_budget=core_variable("channel_budget", Integer()),
        text_configuration=core_variable("text_configuration", Text()),
    )


def _observed_vector():
    observed = core_variable("observed", JSONB())
    items = _items(_field(observed, "values")["items"], ordinal=True)
    values = select(cast(func.data.record_source_float(items.c.value), REAL())).order_by(
        items.c.ordinal
    )
    query = _query_node(select(_query_array(values, REAL())))
    assert query.targetList
    query.targetList[0].val = ast.TypeCast(
        arg=query.targetList[0].val, typeName=pg_type("public", "vector")
    )
    return NativeRoutine(
        "ops",
        "ddo_contextual_observed_vector",
        parameters=(Parameter("observed", pg_type("jsonb")),),
        returns=pg_type("public", "vector"),
        body=query,
        volatility="immutable",
        strict=True,
        search_path=("pg_catalog", "pg_temp"),
    )


def _vector_rows():
    inventory = core_variable("inventory_", JSONB())
    vectors = core_variable("p_vectors", JSONB())
    target = core_variable("target", JSONB())
    observed = core_variable("observed", JSONB())
    items = _items(vectors["vectors"]["items"])
    target_id = target["target_id"].astext
    lexical = _items(func.data.record_source_json(vectors["lexical_targets"], type_=JSONB()))
    lexical_text = core_variable("lexical_text", Text())
    lexical_forms = core_variable("lexical_forms", ARRAY(Text))
    output = (
        ("inventory_id", pg_type("text")),
        ("profile_id", pg_type("text")),
        ("target_id", pg_type("text")),
        ("vector", pg_type("public", "vector")),
        ("search_text", pg_type("text")),
        ("exact_forms", _text_array_type()),
    )
    returns = pg_type("record")
    returns.setof = True
    declaration = NativeRoutine(
        "ops",
        "ddo_contextual_vector_rows",
        parameters=(
            Parameter("p_inventory", pg_type("jsonb")),
            Parameter("p_vectors", pg_type("jsonb")),
        ),
        returns=returns,
        table_columns=output,
        volatility="immutable",
        strict=True,
        search_path=("pg_catalog", "pg_temp"),
        body=Block(
            (
                ForQuery(
                    ("target",),
                    select(_items(inventory["targets"]).c.value),
                    (
                        SelectInto(
                            select(items.c.value).where(
                                _field(items.c.value, "object_id")["text"].astext.collate("C")
                                == target_id.collate("C")
                            ),
                            ("observed",),
                            strict=True,
                        ),
                        If(
                            or_(
                                *(
                                    _field(observed, name)["text"].astext.is_distinct_from(
                                        target[name].astext
                                    )
                                    for name in ("source_binding", "representation_digest")
                                )
                            ),
                            (
                                Raise(
                                    "native score target differs from exact frozen representation",
                                    "23514",
                                ),
                            ),
                        ),
                        SelectInto(
                            select(
                                lexical.c.value["search_text"].astext,
                                _query_array(
                                    select(
                                        _items(lexical.c.value["exact_forms"], text=True).c.value
                                    ).correlate(lexical),
                                    Text(),
                                ),
                            ).where(
                                lexical.c.value["target_id"].astext.collate("C")
                                == target_id.collate("C")
                            ),
                            ("lexical_text", "lexical_forms"),
                            strict=True,
                        ),
                        ReturnQuery(
                            select(
                                inventory["inventory_id"].astext,
                                _field(observed, "profile_id")["text"].astext,
                                target_id,
                                func.ops.ddo_contextual_observed_vector(observed),
                                lexical_text,
                                lexical_forms,
                            )
                        ),
                    ),
                ),
            ),
            locals=(
                Local(
                    "inventory_",
                    pg_type("jsonb"),
                    func.data.record_source_json(
                        core_variable("p_inventory", JSONB())["inventory"]
                    ),
                ),
                Local("target", pg_type("jsonb")),
                Local("observed", pg_type("jsonb")),
                Local("lexical_text", pg_type("text")),
                Local("lexical_forms", _text_array_type()),
            ),
        ),
    )
    return declaration


def _native_scores():
    from .contextual_numerics import default_retrieval_numerics
    from .contextual_scores import SCORE_VERSION
    from .native_catalog import _catalog

    policy = default_retrieval_numerics()
    query, inventory_arg, vectors, policy_arg, numerics = (
        core_variable(name, JSONB())
        for name in ("p_query", "p_inventory", "p_vectors", "p_policy", "numerics")
    )
    inventory = core_variable("inventory_", JSONB())
    inventory_key, profile_key, lexical_query, configuration = (
        core_variable(name, Text())
        for name in ("inventory_key", "profile_key", "lexical_query", "text_configuration")
    )
    target_keys = core_variable("target_keys", ARRAY(Text))
    channel_budget = core_variable("channel_budget", Integer())
    observed = core_variable("observed", JSONB())
    membership, hits = (core_variable(name, JSONB()) for name in ("membership", "hits"))
    extension = _catalog("pg_extension", extname=Text, extversion=Text)
    version = (
        select(extension.c.extversion).where(extension.c.extname == "vector").scalar_subquery()
    )
    budget = cast(policy_arg["budget"].astext, Integer())
    backend_mismatch = or_(
        cast(func.current_setting("server_version_num"), Integer()).is_distinct_from(
            cast(numerics["postgres_version_num"].astext, Integer())
        ),
        version.is_distinct_from(numerics["pgvector_extension_version"].astext),
        *(
            numerics[name].astext.is_distinct_from(getattr(policy, name))
            for name in (
                "target_collation",
                "linguistic_policy",
                "alias_target_normalization",
                "alias_query_normalization",
                "distance_operator",
                "score_transport",
            )
        ),
        configuration.is_distinct_from(policy.text_configuration),
        lexical_query.is_(None),
        func.length(func.btrim(lexical_query)) == 0,
        and_(budget >= 1, budget <= channel_budget).is_not(True),
    )
    items = _items(vectors["vectors"]["items"])
    score_rows = _score_query().cte("score_rows")
    empty = cast(literal("[]", Text()), JSONB())
    membership_rows = func.coalesce(
        func.jsonb_agg(
            aggregate_order_by(
                func.to_jsonb(score_rows.c.target_id), score_rows.c.target_id.collate("C")
            )
        ).filter(score_rows.c.kind == "membership"),
        empty,
    )
    score_hits = func.coalesce(
        func.jsonb_agg(
            aggregate_order_by(
                func.jsonb_build_object(
                    "channel",
                    score_rows.c.channel,
                    "target_id",
                    score_rows.c.target_id,
                    "rank",
                    score_rows.c.rank,
                    "score_float8_hex",
                    func.encode(func.float8send(score_rows.c.score), "hex"),
                ),
                score_rows.c.channel.collate("C"),
                score_rows.c.rank,
                score_rows.c.target_id.collate("C"),
            )
        ).filter(score_rows.c.kind == "hit"),
        empty,
    )
    targets = _items(inventory["targets"])
    return NativeRoutine(
        "ops",
        "ddo_contextual_native_scores",
        parameters=tuple(
            Parameter(name, pg_type("jsonb"))
            for name in ("p_query", "p_inventory", "p_vectors", "p_policy", "numerics")
        ),
        returns=pg_type("jsonb"),
        volatility="stable",
        search_path=("pg_catalog", "pg_temp"),
        body=Block(
            (
                If(
                    backend_mismatch,
                    (
                        Raise(
                            "native score backend/query/budgets differ from exact declared policy",
                            "23514",
                        ),
                    ),
                ),
                SelectInto(
                    select(items.c.value).where(
                        _field(items.c.value, "object_id")["text"].astext.collate("C")
                        == query["occurrence_id"].astext.collate("C"),
                        _field(items.c.value, "vector_id")["text"].astext
                        == query["query_vector_id"].astext,
                    ),
                    ("observed",),
                    strict=True,
                ),
                Assign("query_vector", func.ops.ddo_contextual_observed_vector(observed)),
                Assign("profile_key", _field(observed, "profile_id")["text"].astext),
                SelectInto(select(membership_rows, score_hits), ("membership", "hits")),
                If(
                    membership.is_distinct_from(func.to_jsonb(target_keys)),
                    (Raise("native scoring membership is incomplete or duplicated", "23514"),),
                ),
                Return(
                    func.jsonb_build_object(
                        "version",
                        SCORE_VERSION,
                        "inventory_id",
                        inventory_key,
                        "profile_id",
                        profile_key,
                        "occurrence_id",
                        query["occurrence_id"].astext,
                        "query_vector_id",
                        query["query_vector_id"].astext,
                        "lexical_query",
                        lexical_query,
                        "membership",
                        membership,
                        "hits",
                        hits,
                        "linguistic_observation",
                        func.data.record_json_source(func.ops.ddo_contextual_linguistic_context()),
                    )
                ),
            ),
            locals=(
                Local(
                    "inventory_",
                    pg_type("jsonb"),
                    func.data.record_source_json(inventory_arg["inventory"]),
                ),
                Local("inventory_key", pg_type("text"), inventory["inventory_id"].astext),
                Local("profile_key", pg_type("text")),
                Local(
                    "target_keys",
                    _text_array_type(),
                    _query_array(
                        select(targets.c.value["target_id"].astext).order_by(
                            targets.c.value["target_id"].astext.collate("C")
                        ),
                        Text(),
                    ),
                ),
                Local("query_vector", pg_type("public", "vector")),
                Local("observed", pg_type("jsonb")),
                Local("lexical_query", pg_type("text"), query["lexical_query"].astext),
                Local(
                    "channel_budget",
                    pg_type("int4"),
                    cast(policy_arg["channel_budget"].astext, Integer()),
                ),
                Local("text_configuration", pg_type("text"), numerics["text_configuration"].astext),
                Local("membership", pg_type("jsonb")),
                Local("hits", pg_type("jsonb")),
            ),
        ),
    )


def _score_meaning():
    scores = core_variable("scores", JSONB())
    empty = cast(literal("[]", Text()), JSONB())
    members = _items(scores["membership"], text=True, ordinal=True)
    hits = _items(scores["hits"], ordinal=True)
    member_meaning = select(
        func.coalesce(
            func.jsonb_agg(
                aggregate_order_by(
                    func.jsonb_build_array("string", members.c.value),
                    members.c.ordinal,
                )
            ),
            empty,
        )
    ).scalar_subquery()
    hit_meaning = func.jsonb_build_array(
        "mapping",
        func.jsonb_build_array(
            *(
                func.jsonb_build_array(
                    name, func.jsonb_build_array(kind, hits.c.value[name].astext)
                )
                for name, kind in (
                    ("channel", "string"),
                    ("target_id", "string"),
                    ("rank", "integer"),
                    ("score_float8_hex", "string"),
                )
            )
        ),
    )
    hit_meanings = select(
        func.coalesce(func.jsonb_agg(aggregate_order_by(hit_meaning, hits.c.ordinal)), empty)
    ).scalar_subquery()
    meaning = func.data.ddo_normalize(
        func.jsonb_build_array(
            "mapping",
            func.jsonb_build_array(
                *(
                    func.jsonb_build_array(
                        name, func.jsonb_build_array("string", scores[name].astext)
                    )
                    for name in (
                        "version",
                        "inventory_id",
                        "profile_id",
                        "occurrence_id",
                        "query_vector_id",
                        "lexical_query",
                    )
                ),
                func.jsonb_build_array(
                    "linguistic_observation",
                    func.data.record_json_meaning(scores["linguistic_observation"]),
                ),
                func.jsonb_build_array(
                    "membership", func.jsonb_build_array("sequence", member_meaning)
                ),
                func.jsonb_build_array("hits", func.jsonb_build_array("sequence", hit_meanings)),
            ),
        )
    )
    return NativeRoutine(
        "ops",
        "ddo_contextual_score_meaning",
        parameters=(Parameter("scores", pg_type("jsonb")),),
        returns=pg_type("jsonb"),
        body=select(meaning),
        volatility="immutable",
        strict=True,
        search_path=("pg_catalog", "pg_temp"),
    )


def contextual_scoring_native_programs() -> tuple[ProgramDeclaration, ...]:
    return tuple(
        ProgramDeclaration(
            routine,
            source="data-operations:forward",
            owner=role_name("publisher"),
            access=INTERNAL_PROGRAM,
        )
        for routine in (_observed_vector(), _vector_rows(), _native_scores(), _score_meaning())
    )


def contextual_scoring_native_sql() -> str:
    """Render captured definitions followed by their existing PUBLIC revocations."""
    declarations = contextual_scoring_native_programs()
    definitions = tuple(declaration.routine.render() for declaration in declarations)
    revocations = tuple(
        native_privilege_sql(declaration.identity, "PUBLIC", grant=False)
        for declaration in declarations
    )
    return ";\n".join((*definitions, *revocations)) + ";"
