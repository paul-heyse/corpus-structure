"""Compile scoped visual evidence reads against captured physical and DTO contracts."""

from sqlalchemy import (
    BigInteger,
    Integer,
    MetaData,
    Numeric,
    Text,
    and_,
    case,
    cast,
    column,
    exists,
    func,
    literal,
    or_,
    select,
    union,
)
from sqlalchemy.dialects.postgresql import BYTEA, JSON, JSONB, aggregate_order_by
from sqlalchemy.sql import quoted_name

from corpus_structure.schema.integrity import role_name

from .data_read_boundary_native import read_presentation_check
from .native_objects import INTERNAL_PROGRAM, native_sql_script
from .native_program import (
    Assign,
    Block,
    If,
    Local,
    NativeRoutine,
    Parameter,
    Perform,
    Raise,
    Return,
    SelectInto,
    core_relation_row,
    core_variable,
    pg_type,
    variable,
)
from .native_program_registry import ProgramDeclaration


def _object(**values):
    return func.jsonb_build_object(
        *(item for pair in values.items() for item in pair), type_=JSONB()
    )


def _elements(value, name, *, ordinal=False):
    options = {"with_ordinality": "ordinality"} if ordinal else {}
    return (
        func.jsonb_array_elements(value)
        .table_valued(column("value", JSONB()), **options)
        .render_derived(name=name)
    )


def _json(value):
    return cast(literal(value), JSONB())


def _folded_text(value):
    # Match PostgreSQL's Unicode case folding and Python's split whitespace set.
    spaces = (
        "[\u0009-\u000d\u001c-\u0020\u0085\u00a0\u1680\u2000-\u200a\u2028\u2029\u202f\u205f\u3000]+"
    )
    folded = func.casefold(value.collate(quoted_name("pg_catalog.pg_unicode_fast", False)))
    return func.btrim(func.regexp_replace(folded, spaces, " ", "g"), " ")


def _visual_candidate_routine() -> NativeRoutine:
    """Preserve parent-first artifact ordinals through all candidate filters."""
    mapped = core_variable("mapped", JSONB())
    request = core_variable("p", JSONB())
    after, limit, cell_index = (
        cast(request[name].astext, Integer()) for name in ("after", "limit", "cell_index")
    )
    occurrence = request["occurrence_id"].astext
    elements = _elements(mapped["rows"], "row", ordinal=True)
    entries = select(
        elements.c.value.label("body"), cast(elements.c.ordinality, Integer()).label("ordinal")
    ).cte("entries")
    anchor = (
        select(entries.c.body)
        .where(entries.c.body["occurrence_id"].astext == occurrence)
        .cte("anchor")
    )
    cell_root = select(
        anchor.c.body["cells"][cell_index]["content_occurrence_id"].astext.label("id")
    ).cte("cell_root")
    subtree = (
        select(entries.c.body, entries.c.ordinal)
        .where(entries.c.body["occurrence_id"].astext == select(cell_root.c.id).scalar_subquery())
        .cte("subtree", recursive=True)
    )
    parent = subtree.alias("parent")
    subtree = subtree.union_all(
        select(entries.c.body, entries.c.ordinal).select_from(
            entries.join(
                parent,
                entries.c.body["parent_occurrence_id"].astext
                == parent.c.body["occurrence_id"].astext,
            )
        )
    )
    text_matches = (
        select(entries.c.body)
        .where(
            entries.c.body["kind"].astext.in_(
                ("picture_text", "picture_description", "caption", "caption_candidate")
            ),
            func.strpos(
                _folded_text(entries.c.body["text"].astext), _folded_text(request["query"].astext)
            )
            > 0,
        )
        .cte("text_matches")
    )
    ancestors = select(text_matches.c.body).cte("text_ancestors", recursive=True)
    child = ancestors.alias("child")
    ancestors = ancestors.union_all(
        select(entries.c.body).select_from(
            entries.join(
                child,
                entries.c.body["occurrence_id"].astext
                == child.c.body["parent_occurrence_id"].astext,
            )
        )
    )
    targets = union(
        select(ancestors.c.body["occurrence_id"].astext.label("id")).where(
            ancestors.c.body["kind"].astext == "picture"
        ),
        select(
            func.jsonb_array_elements_text(
                text_matches.c.body["parser_attachment_occurrence_ids"]
            ).label("id")
        ),
        select(
            func.jsonb_array_elements_text(
                text_matches.c.body["associated_picture_occurrence_ids"]
            ).label("id")
        ),
    ).cte("targets")
    body = entries.c.body
    regions = _elements(request["regions"], "region")
    source_region = body["source_region"]
    intersects = exists(
        select(1)
        .select_from(regions)
        .where(
            source_region.is_not(None),
            source_region != _json("null"),
            cast(source_region["left"].astext, Numeric())
            < cast(regions.c.value["right"].astext, Numeric()),
            cast(regions.c.value["left"].astext, Numeric())
            < cast(source_region["right"].astext, Numeric()),
            cast(source_region["top"].astext, Numeric())
            < cast(regions.c.value["bottom"].astext, Numeric()),
            cast(regions.c.value["top"].astext, Numeric())
            < cast(source_region["bottom"].astext, Numeric()),
        )
    )
    candidates = (
        select(entries)
        .where(
            entries.c.ordinal > after,
            or_(request["kind"].astext.is_(None), body["kind"].astext == request["kind"].astext),
            or_(
                occurrence.is_(None),
                case(
                    (
                        request["cell_index"].astext.is_(None),
                        body["occurrence_id"].astext == occurrence,
                    ),
                    else_=entries.c.ordinal.in_(select(subtree.c.ordinal)),
                ),
            ),
            or_(
                request["query"].astext.is_(None),
                and_(
                    body["kind"].astext == "picture",
                    body["occurrence_id"].astext.in_(select(targets.c.id)),
                ),
            ),
            or_(func.jsonb_array_length(request["regions"]) == 0, intersects),
        )
        .order_by(entries.c.ordinal)
        .limit(limit + 1)
        .cte("candidates")
    )
    ranked = select(
        candidates, func.row_number().over(order_by=candidates.c.ordinal).label("n")
    ).cte("ranked")
    page = select(
        func.coalesce(
            func.jsonb_agg(aggregate_order_by(ranked.c.body, ranked.c.ordinal)).filter(
                ranked.c.n <= limit
            ),
            _json("[]"),
        ),
        case(
            (func.max(ranked.c.n) > limit, func.max(ranked.c.ordinal).filter(ranked.c.n <= limit)),
            else_=None,
        ),
    )
    retained = _elements(mapped["rows"], "retained")
    steps = (
        If(
            mapped.is_(None),
            (
                If(after != 0, (Raise("visual evidence has no mapped continuation", "23514"),)),
                Return(_object(kind="rows", items=_json("[]"), next_after=None)),
            ),
        ),
        SelectInto(page, ("rows_", "following")),
        If(
            and_(
                occurrence.is_not(None),
                ~exists(
                    select(1)
                    .select_from(retained)
                    .where(retained.c.value["occurrence_id"].astext == occurrence)
                ),
            ),
            (Raise("visual occurrence is outside candidate artifact", "23514"),),
        ),
        If(
            and_(
                request["cell_index"].astext.is_not(None),
                ~exists(
                    select(1)
                    .select_from(retained)
                    .where(
                        retained.c.value["occurrence_id"].astext == occurrence,
                        retained.c.value["kind"].astext == "table",
                        retained.c.value["cells"][cell_index][
                            "content_occurrence_id"
                        ].astext.is_not(None),
                    )
                ),
            ),
            (Raise("visual cell has no exact retained content group", "23514"),),
        ),
        If(
            and_(after > 0, func.jsonb_array_length(core_variable("rows_", JSONB())) == 0),
            (Raise("visual continuation is outside selected scope", "23514"),),
        ),
        Return(
            _object(
                kind="rows",
                items=core_variable("rows_", JSONB()),
                next_after=core_variable("following", Integer()),
            )
        ),
    )
    return NativeRoutine(
        "ops",
        "ddo_visual_candidate_rows",
        parameters=(Parameter("mapped", pg_type("jsonb")), Parameter("p", pg_type("jsonb"))),
        returns=pg_type("jsonb"),
        body=Block(
            steps, (Local("rows_", pg_type("jsonb")), Local("following", pg_type("integer")))
        ),
        volatility="immutable",
        security_definer=True,
        search_path=("pg_catalog", "pg_temp"),
    )


def _selected_visual_program(model: MetaData, artifact_schema: bytes) -> NativeRoutine:
    products = model.tables["kb.data_product"]
    reads = model.tables["ops.data_demand_read"]
    episodes = model.tables["ops.data_derivation"]
    intents = model.tables["ops.data_completion_intent"]
    kinds = model.tables["sem.data_kind_contract"]
    inputs = model.tables["ops.data_derivation_input"]
    support = model.tables["ops.data_derivation_support"]
    request = core_variable("p_payload", JSONB())
    values = {
        name: core_variable(name, JSONB())
        for name in (
            "source",
            "cut",
            "body",
            "observation",
            "image",
            "mapping",
            "raw_pin",
            "raw_input",
            "mapped",
            "result",
        )
    }
    binaries = {
        name: core_variable(name, BYTEA()) for name in ("artifact", "image_bytes", "response_bytes")
    }
    integers = {name: core_variable(name, Integer()) for name in ("total", "offset_", "length_")}
    kind, digest, media = (core_variable(name, Text()) for name in ("kind", "digest", "media"))

    def row(name, relation, field):
        return core_variable(name, relation.c[field].type, field)

    project_id = row("product", products, "project_id")
    original_source = row("product", products, "original_source")
    episode_id = row("episode", episodes, "id")
    raw_values = _elements(row("intent", intents, "payload")["inputs"], "selected")
    input_episode = func.ops.ddo_single_input_support_episode(values["raw_input"])
    namespace = "https://corpus-structure.dev/semantic/data-operation-visual/"
    selected_pin = (
        request["source"]["demand_id"].astext,
        request["source"]["read_id"].astext,
    )
    mapping_steps = (
        Assign("mapping", values["body"]),
        Assign("observation", values["body"]["observation"]),
        SelectInto(
            select(core_relation_row(intents)).where(
                intents.c.id == row("episode", episodes, "intent_id")
            ),
            ("intent",),
            strict=True,
        ),
        SelectInto(
            select(raw_values.c.value).where(
                raw_values.c.value["role"].astext == "observation",
                raw_values.c.value["member_id"].astext.is_(None),
            ),
            ("raw_input",),
            strict=True,
        ),
        If(
            or_(
                ~exists(
                    select(1)
                    .select_from(inputs)
                    .where(
                        inputs.c.derivation_id == episode_id,
                        inputs.c.role == "observation",
                        inputs.c.product_id == values["raw_input"]["product_id"].astext,
                        inputs.c.member_id.is_(None),
                    )
                ),
                ~exists(
                    select(1)
                    .select_from(support)
                    .where(
                        support.c.derivation_id == episode_id,
                        support.c.support_derivation_id == input_episode,
                    )
                ),
            ),
            (Raise("visual mapping lacks exact admitted raw input", "23514"),),
        ),
        Assign(
            "raw_pin",
            _object(
                use_id=request["evidence"]["use_id"].astext,
                product_id=values["raw_input"]["product_id"].astext,
                derivation_id=input_episode,
            ),
        ),
        Perform(
            func.ops.ddo_require_selected_output(
                *selected_pin,
                values["raw_pin"]["use_id"].astext,
                values["raw_pin"]["product_id"].astext,
                values["raw_pin"]["derivation_id"].astext,
            )
        ),
        SelectInto(
            select(core_relation_row(products)).where(
                products.c.id == values["raw_pin"]["product_id"].astext,
                products.c.project_id == project_id,
                products.c.original_source == original_source,
            ),
            ("raw_product",),
            strict=True,
        ),
        If(
            or_(
                ~exists(
                    select(1)
                    .select_from(kinds)
                    .where(
                        kinds.c.kind_contract == row("raw_product", products, "kind_contract"),
                        kinds.c.kind == namespace + "DdoChandraObservation",
                    )
                ),
                func.data.ddo_json(
                    row("raw_product", products, "canonical_body"), type_=JSONB()
                ).is_distinct_from(values["observation"]),
            ),
            (Raise("visual mapping differs from its admitted raw observation", "23514"),),
        ),
        SelectInto(
            select(core_relation_row(episodes)).where(
                episodes.c.id == values["raw_pin"]["derivation_id"].astext
            ),
            ("raw_episode",),
            strict=True,
        ),
    )
    image = values["image"]
    publication = values["source"]["receipt"]["publication"]

    def png_integer(offset):
        return sum(
            (
                cast(func.get_byte(binaries["image_bytes"], offset), BigInteger()) * 16777216,
                func.get_byte(binaries["image_bytes"], offset + 1) * 65536,
                func.get_byte(binaries["image_bytes"], offset + 2) * 256,
                func.get_byte(binaries["image_bytes"], offset + 3),
            )
        )

    mapped_steps = (
        Assign("artifact", func.decode(values["mapping"]["mapped_hex"].astext, "hex")),
        If(
            func.octet_length(binaries["artifact"]) > 8388608,
            (Raise("visual mapped artifact exceeds byte bound", "54000"),),
        ),
        Assign("mapped", cast(func.convert_from(binaries["artifact"], "UTF8"), JSONB())),
        If(
            or_(
                ~func.public.json_matches_schema(
                    cast(literal(artifact_schema.decode()), JSON()), cast(values["mapped"], JSON())
                ),
                cast(values["mapped"]["page_no"].astext, Integer())
                != cast(image["page_no"].astext, Integer()),
            ),
            (Raise("visual mapped artifact violates current candidate schema", "23514"),),
        ),
    )
    header = _object(
        kind="header",
        header=_object(
            evidence=request["evidence"],
            raw=values["raw_pin"],
            producer=func.to_jsonb(core_variable("episode", episodes.table_valued().type)),
            raw_producer=func.to_jsonb(core_variable("raw_episode", episodes.table_valued().type)),
            observation=values["observation"]
            .op("-")("raw_response")
            .op("-")("image")
            .op("||")(
                _object(
                    image=image.op("-")("content_hex")
                    .op("-")("transform_json")
                    .op("||")(_object(transform=cast(image["transform_json"].astext, JSONB())))
                )
            ),
            mapping_availability=case(
                (values["mapping"].is_(None), "not_selected"),
                (values["mapped"].is_(None), "unavailable"),
                else_="available",
            ),
            mapping=case(
                (values["mapping"].is_(None), None),
                else_=values["mapping"].op("-")("observation").op("-")("mapped_hex"),
            ),
            mapped_digest=case(
                (values["mapped"].is_(None), None),
                else_=func.encode(func.sha256(binaries["artifact"]), "hex"),
            ),
        ),
    )
    artifact_steps = (
        Assign("digest", request["artifact_digest"].astext),
        If(
            digest == image["content_digest"].astext,
            (Assign("artifact", binaries["image_bytes"]), Assign("media", literal("image/png"))),
            (
                If(
                    digest == values["observation"]["response_digest"].astext,
                    (
                        Assign("artifact", binaries["response_bytes"]),
                        Assign("media", literal("text/html; charset=utf-8")),
                    ),
                    (
                        If(
                            and_(
                                values["mapped"].is_not(None),
                                digest == func.encode(func.sha256(binaries["artifact"]), "hex"),
                            ),
                            (Assign("media", literal("application/json")),),
                            (Raise("visual artifact is outside exact selected evidence", "23514"),),
                        ),
                    ),
                ),
            ),
        ),
        Assign("total", func.octet_length(binaries["artifact"])),
        Assign("offset_", cast(request["after"].astext, Integer())),
        If(
            or_(
                integers["offset_"] > integers["total"],
                and_(integers["offset_"] == integers["total"], integers["offset_"] != 0),
            ),
            (Raise("visual byte continuation is outside artifact", "23514"),),
        ),
        Assign("length_", func.least(65536, integers["total"] - integers["offset_"])),
        Assign(
            "result",
            _object(
                kind="artifact",
                digest=digest,
                media_type=media,
                content_hex=func.encode(
                    func.substr(binaries["artifact"], integers["offset_"] + 1, integers["length_"]),
                    "hex",
                ),
                offset=integers["offset_"],
                total_bytes=integers["total"],
                next_offset=case(
                    (
                        integers["offset_"] + integers["length_"] < integers["total"],
                        integers["offset_"] + integers["length_"],
                    ),
                    else_=None,
                ),
            ),
        ),
    )
    steps = (
        Assign(
            "source",
            func.ops.ddo_impl_read_selected_pdf_source(request["source"], type_=JSONB())["payload"],
        ),
        Assign(
            "cut",
            func.ops.ddo_require_selected_output(
                *selected_pin,
                request["evidence"]["use_id"].astext,
                request["evidence"]["product_id"].astext,
                request["evidence"]["derivation_id"].astext,
            ),
        ),
        If(
            values["cut"].is_distinct_from(values["source"]["cut"]),
            (Raise("visual evidence differs from selected source cut", "23514"),),
        ),
        SelectInto(
            select(core_relation_row(reads)).where(
                reads.c.id == request["source"]["read_id"].astext,
                reads.c.demand_id == request["source"]["demand_id"].astext,
            ),
            ("boundary",),
            strict=True,
        ),
        read_presentation_check(
            row("boundary", reads, "scope"), row("boundary", reads, "public_disclosure")
        ),
        SelectInto(
            select(core_relation_row(products)).where(
                products.c.id == request["evidence"]["product_id"].astext,
                products.c.project_id == request["source"]["project_id"].astext,
            ),
            ("product",),
            strict=True,
        ),
        SelectInto(
            select(kinds.c.kind).where(
                kinds.c.kind_contract == row("product", products, "kind_contract")
            ),
            ("kind",),
            strict=True,
        ),
        SelectInto(
            select(core_relation_row(episodes)).where(
                episodes.c.id == request["evidence"]["derivation_id"].astext
            ),
            ("episode",),
            strict=True,
        ),
        Assign("body", func.data.ddo_json(row("product", products, "canonical_body"))),
        Assign("raw_pin", request["evidence"]),
        Assign("raw_episode", variable("episode")),
        If(
            kind == namespace + "DdoVisualMapping",
            mapping_steps,
            (
                If(
                    kind == namespace + "DdoChandraObservation",
                    (Assign("observation", values["body"]),),
                    (Raise("selected product is not visual evidence", "23514"),),
                ),
            ),
        ),
        Assign("image", values["observation"]["image"]),
        If(
            or_(
                original_source.is_distinct_from(image["document"].astext),
                original_source.is_distinct_from(values["source"]["original_source"].astext),
                image["source_digest"].astext.is_distinct_from(publication["source_digest"].astext),
                image["logical_digest"].astext.is_distinct_from(
                    publication["logical_digest"].astext
                ),
            ),
            (Raise("visual image differs from selected original PDF source", "23514"),),
        ),
        Assign("image_bytes", func.decode(image["content_hex"].astext, "hex")),
        Assign(
            "response_bytes", func.convert_to(values["observation"]["raw_response"].astext, "UTF8")
        ),
        If(
            or_(
                func.encode(func.sha256(binaries["image_bytes"]), "hex").is_distinct_from(
                    image["content_digest"].astext
                ),
                func.substr(binaries["image_bytes"], 1, 8).is_distinct_from(
                    func.decode("89504e470d0a1a0a", "hex")
                ),
                func.octet_length(binaries["image_bytes"]) < 24,
                png_integer(16) != cast(image["width"].astext, Integer()),
                png_integer(20) != cast(image["height"].astext, Integer()),
                func.encode(func.sha256(binaries["response_bytes"]), "hex").is_distinct_from(
                    values["observation"]["response_digest"].astext
                ),
            ),
            (Raise("visual retained bytes differ from their exact digests", "23514"),),
        ),
        If(
            and_(values["mapping"].is_not(None), values["mapping"]["mapped_hex"].astext != ""),
            mapped_steps,
        ),
        If(
            request["mode"].astext == "header",
            (Assign("result", header),),
            (
                If(
                    request["mode"].astext == "artifact",
                    artifact_steps,
                    (
                        If(
                            request["mode"].astext == "rows",
                            (
                                Assign(
                                    "result",
                                    func.ops.ddo_visual_candidate_rows(values["mapped"], request),
                                ),
                            ),
                            (Raise("unknown visual read mode", "23514"),),
                        ),
                    ),
                ),
            ),
        ),
        If(
            func.octet_length(cast(values["result"], Text()))
            > cast(request["max_bytes"].astext, Integer()),
            (Raise("visual result exceeds byte bound", "54000"),),
        ),
        Return(_object(payload=values["result"])),
    )
    return NativeRoutine(
        "ops",
        "read_selected_visual_evidence",
        parameters=(Parameter("p_payload", pg_type("jsonb")),),
        returns=pg_type("jsonb"),
        body=Block(
            steps,
            (
                *(Local(name, pg_type("jsonb")) for name in values),
                *(Local(name, pg_type("bytea")) for name in binaries),
                *(Local(name, pg_type("integer")) for name in integers),
                *(Local(name, pg_type("text")) for name in ("kind", "digest", "media")),
                Local("product", products),
                Local("boundary", reads),
                Local("raw_product", products),
                Local("episode", episodes),
                Local("raw_episode", episodes),
                Local("intent", intents),
            ),
        ),
        volatility="volatile",
        security_definer=True,
        search_path=("pg_catalog", "pg_temp"),
    )


def visual_read_native_programs(
    model: MetaData, artifact_schema: bytes
) -> tuple[ProgramDeclaration, ...]:
    return tuple(
        ProgramDeclaration(
            routine,
            source="data-operation-source-admission:forward",
            owner=role_name("publisher"),
            access=INTERNAL_PROGRAM,
        )
        for routine in (
            _visual_candidate_routine(),
            _selected_visual_program(model, artifact_schema),
        )
    )


def visual_read_programs(model: MetaData, artifact_schema: bytes) -> str:
    """Render the protected candidate/visual implementations before wire projection."""
    return native_sql_script(
        item.routine.render() for item in visual_read_native_programs(model, artifact_schema)
    )
