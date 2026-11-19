"""Compile selected native source projection and sealed PDF observation custody."""

from typing import Any, Literal

from sqlalchemy import (
    BigInteger,
    Boolean,
    Text,
    and_,
    any_,
    case,
    cast,
    column,
    exists,
    func,
    literal,
    or_,
    select,
    true,
    tuple_,
    union_all,
)
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, aggregate_order_by, array
from sqlalchemy.types import TypeEngine

from corpus_structure.schema.integrity import role_name

from .data_read_boundary_native import read_presentation_check
from .native_objects import INTERNAL_PROGRAM, NativeProgramAccess, native_sql_script
from .native_program import (
    Assign,
    Block,
    ForQuery,
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
)
from .native_program import literal as pg_literal
from .native_program_registry import ProgramDeclaration


def _json(value):
    return cast(literal(value), JSONB())


def _items(value, name, *, ordinal=False, text=False):
    source = func.jsonb_array_elements_text(value) if text else func.jsonb_array_elements(value)
    datatype: TypeEngine[Any] = Text() if text else JSONB()
    return source.table_valued(
        column("value", datatype), **({"with_ordinality": "ordinal"} if ordinal else {})
    ).render_derived(name=name)


def _field(name, relation, field):
    return core_variable(name, relation.c[field].type, field)


def _load(name, relation, *conditions):
    return SelectInto(
        select(core_relation_row(relation)).select_from(relation).where(*conditions),
        (name,),
        strict=True,
    )


def _refuse(condition, message, state="23514"):
    return If(condition, (Raise(message, state),))


def _routine(
    name,
    parameters,
    steps,
    *,
    locals_=(),
    result=None,
    volatility: Literal["stable", "volatile", "immutable"] = "stable",
    strict=False,
    protected=True,
    access=INTERNAL_PROGRAM,
):
    routine = NativeRoutine(
        "ops",
        name,
        parameters=parameters,
        returns=result or pg_type("jsonb"),
        body=Block(steps, locals_),
        volatility=volatility,
        strict=strict,
        security_definer=protected,
        search_path=("pg_catalog", "pg_temp"),
    )
    return ProgramDeclaration(
        routine,
        source="data-operation-source-admission:forward",
        owner=role_name("publisher"),
        access=access,
    )


def _native_source_body():
    text_names = ("p_document", "p_section", "p_membership", "p_projection_digest")
    document, section, membership, projection_digest = (
        core_variable(name, Text()) for name in text_names
    )
    projection, inputs, selectors = (
        core_variable(name, JSONB()) for name in ("p_projection", "p_items", "p_selectors")
    )
    values = {
        name: core_variable(name, JSONB())
        for name in (
            "atom",
            "original",
            "piece",
            "selector",
            "cell",
            "retained_cell",
            "table_data",
            "cells",
            "atoms",
            "ancestors",
            "all_atoms",
            "pieces",
            "recognition",
            "selected",
            "coordinate",
        )
    }
    atom, original, piece, selector = (
        values[name] for name in ("atom", "original", "piece", "selector")
    )
    cell, retained_cell, table_data, cells = (
        values[name] for name in ("cell", "retained_cell", "table_data", "cells")
    )
    atoms, ancestors, all_atoms, pieces = (
        values[name] for name in ("atoms", "ancestors", "all_atoms", "pieces")
    )
    recognition, selected, coordinate = (
        values[name] for name in ("recognition", "selected", "coordinate")
    )
    name = core_variable("name", Text())
    pointers = core_variable("pointers", ARRAY(Text()))
    text_value = core_variable("text_value", Text())
    previous = core_variable("previous", BigInteger())
    projection_id = core_variable("projection", Text())
    object_, append = func.jsonb_build_object, func.jsonb_build_array

    def retain(target_name, source, fields):
        destination = values[target_name]
        return ForQuery(
            ("name",),
            select(func.unnest(array(list(fields), type_=Text()))),
            (
                If(
                    source.has_key(name),
                    (Assign(target_name, destination.op("||")(object_(name, source[name]))),),
                ),
            ),
        )

    refs = _items(original[name], "refs", ordinal=True)
    provenance = _items(func.coalesce(original["prov"], _json("[]")), "provenance", ordinal=True)
    original_rows = _items(inputs, "original_items")
    cell_rows = _items(original["data"]["table_cells"], "table_cells")
    original_atoms = _items(all_atoms, "original_atoms")
    requested_items = _items(projection["items"], "requested_items", ordinal=True, text=True)
    requested_ancestors = _items(
        projection["ancestors"], "requested_ancestors", ordinal=True, text=True
    )

    def selected_atoms(requested):
        return select(
            func.coalesce(
                func.jsonb_agg(aggregate_order_by(original_atoms.c.value, requested.c.ordinal)),
                _json("[]"),
            )
        ).select_from(
            requested.join(
                original_atoms, original_atoms.c.value["self_ref"].astext == requested.c.value
            )
        )

    atom_rows = _items(atoms, "selected_atoms")
    piece_rows = _items(projection["pieces"], "source_pieces")
    outcomes = _items(
        func.coalesce(projection["health"]["formula_outcomes"], _json("[]")), "formula_outcomes"
    )
    recorded = _items(recognition, "recorded_recognition")
    selector_rows = _items(selectors, "requested_selectors")
    ancestry_atoms = _items(atoms, "ancestry_atoms")
    ancestry = select(
        ancestry_atoms.c.value["self_ref"].astext.label("pointer"),
        ancestry_atoms.c.value["parent"].astext.label("parent"),
        array([ancestry_atoms.c.value["self_ref"].astext], type_=Text()).label("path"),
    ).cte("ancestry", recursive=True)
    ancestry = ancestry.union_all(
        select(
            original_atoms.c.value["self_ref"].astext,
            original_atoms.c.value["parent"].astext,
            func.array_append(ancestry.c.path, original_atoms.c.value["self_ref"].astext),
        )
        .select_from(
            ancestry.join(
                original_atoms, original_atoms.c.value["self_ref"].astext == ancestry.c.parent
            )
        )
        .where(~(original_atoms.c.value["self_ref"].astext == any_(ancestry.c.path)))
    )
    ancestor_selected = exists(
        select(1)
        .select_from(ancestry)
        .where(ancestry.c.pointer == selector["native_pointer"].astext)
    )
    initial_shape = or_(
        func.nullif(document, "").is_(None),
        func.nullif(section, "").is_(None),
        membership.not_in(("direct", "descendants")),
        func.jsonb_typeof(inputs).is_distinct_from("array"),
        func.jsonb_typeof(selectors).is_distinct_from("array"),
        func.jsonb_array_length(selectors) == 0,
        *(
            func.jsonb_typeof(projection[key]).is_distinct_from(kind)
            for key, kind in (
                ("items", "array"),
                ("ancestors", "array"),
                ("text", "string"),
                ("pieces", "array"),
            )
        ),
    )
    steps = (
        _refuse(initial_shape, "original source projection/request has invalid declared shape"),
        ForQuery(
            ("original",),
            select(original_rows.c.value),
            (
                Assign("atom", _json("{}")),
                retain(
                    "atom",
                    original,
                    (
                        "self_ref",
                        "label",
                        "text",
                        "orig",
                        "name",
                        "level",
                        "content_layer",
                        "marker",
                        "enumerated",
                    ),
                ),
                If(
                    func.jsonb_typeof(original["parent"]["$ref"]) == "string",
                    (Assign("atom", atom.op("||")(object_("parent", original["parent"]["$ref"]))),),
                ),
                ForQuery(
                    ("name",),
                    select(
                        func.unnest(
                            array(["children", "captions", "footnotes", "references"], type_=Text())
                        )
                    ),
                    (
                        If(
                            original.has_key(name),
                            (
                                Assign(
                                    "atom",
                                    atom.op("||")(
                                        object_(
                                            name,
                                            select(
                                                func.coalesce(
                                                    func.jsonb_agg(
                                                        aggregate_order_by(
                                                            refs.c.value["$ref"], refs.c.ordinal
                                                        )
                                                    ),
                                                    _json("[]"),
                                                )
                                            ).scalar_subquery(),
                                        )
                                    ),
                                ),
                            ),
                        ),
                    ),
                ),
                If(
                    original["data"].has_key("table_cells"),
                    (
                        Assign("table_data", _json("{}")),
                        Assign("cells", _json("[]")),
                        retain(
                            "table_data", original["data"], ("num_rows", "num_cols", "orientation")
                        ),
                        ForQuery(
                            ("cell",),
                            select(cell_rows.c.value),
                            (
                                Assign("retained_cell", _json("{}")),
                                retain(
                                    "retained_cell",
                                    cell,
                                    (
                                        "text",
                                        "row_span",
                                        "col_span",
                                        "start_row_offset_idx",
                                        "end_row_offset_idx",
                                        "start_col_offset_idx",
                                        "end_col_offset_idx",
                                        "column_header",
                                        "row_header",
                                        "row_section",
                                        "fillable",
                                    ),
                                ),
                                If(
                                    cell["ref"]["$ref"].astext.is_not(None),
                                    (
                                        Assign(
                                            "retained_cell",
                                            retained_cell.op("||")(
                                                object_("ref", cell["ref"]["$ref"])
                                            ),
                                        ),
                                    ),
                                ),
                                Assign("cells", cells.op("||")(append(retained_cell))),
                            ),
                        ),
                        Assign(
                            "atom",
                            atom.op("||")(
                                object_("data", table_data.op("||")(object_("table_cells", cells)))
                            ),
                        ),
                    ),
                ),
                Assign(
                    "atom",
                    atom.op("||")(
                        object_(
                            "prov",
                            select(
                                func.coalesce(
                                    func.jsonb_agg(
                                        aggregate_order_by(
                                            object_("page_no", provenance.c.value["page_no"]),
                                            provenance.c.ordinal,
                                        )
                                    ),
                                    _json("[]"),
                                )
                            )
                            .where(provenance.c.value.has_key("page_no"))
                            .scalar_subquery(),
                        )
                    ),
                ),
                _refuse(
                    or_(
                        func.nullif(atom["self_ref"].astext, "").is_(None),
                        atom["self_ref"].astext == any_(pointers),
                    ),
                    "original source repeats or lacks an atom address",
                    "P0001",
                ),
                Assign("pointers", func.array_append(pointers, atom["self_ref"].astext)),
                Assign("atoms", atoms.op("||")(append(atom))),
            ),
        ),
        Assign("all_atoms", atoms),
        SelectInto(selected_atoms(requested_items), ("atoms",)),
        SelectInto(selected_atoms(requested_ancestors), ("ancestors",)),
        _refuse(
            or_(
                func.jsonb_array_length(atoms) != func.jsonb_array_length(projection["items"]),
                func.jsonb_array_length(ancestors)
                != func.jsonb_array_length(projection["ancestors"]),
            ),
            "original source selected/ancestor atom inventory is absent or ambiguous",
            "P0001",
        ),
        Assign(
            "pointers",
            select(
                func.coalesce(
                    func.array_agg(atom_rows.c.value["self_ref"].astext), array([], type_=Text())
                )
            ).scalar_subquery(),
        ),
        ForQuery(
            ("original",),
            select(piece_rows.c.value),
            (
                Assign("piece", _json("{}")),
                retain(
                    "piece",
                    original,
                    ("kind", "start", "end", "item_ref", "source_field", "cell_index"),
                ),
                _refuse(
                    or_(
                        piece["start"].astext.op("!~")("^(0|[1-9][0-9]*)$"),
                        piece["end"].astext.op("!~")("^[1-9][0-9]*$"),
                        cast(piece["start"].astext, BigInteger()) != previous,
                        cast(piece["end"].astext, BigInteger()) <= previous,
                        cast(piece["end"].astext, BigInteger()) > func.char_length(text_value),
                        piece["kind"].astext.not_in(("native_text", "synthetic_separator")),
                        and_(
                            piece["kind"].astext == "native_text",
                            or_(
                                ~func.coalesce(piece["item_ref"].astext == any_(pointers), False),
                                func.nullif(piece["source_field"].astext, "").is_(None),
                            ),
                        ),
                    ),
                    "original source pieces do not partition the actual projection",
                ),
                Assign("previous", cast(piece["end"].astext, BigInteger())),
                Assign("pieces", pieces.op("||")(append(piece))),
            ),
        ),
        _refuse(
            previous != func.char_length(text_value),
            "original source pieces omit actual projected text",
            "P0001",
        ),
        ForQuery(
            ("original",),
            select(outcomes.c.value),
            (
                _refuse(
                    or_(
                        ~func.coalesce(original["pointer"].astext == any_(pointers), False),
                        exists(
                            select(1)
                            .select_from(recorded)
                            .where(recorded.c.value["pointer"].astext == original["pointer"].astext)
                        ),
                    ),
                    "original recognition differs from unique source atom inventory",
                    "P0001",
                ),
                Assign(
                    "recognition",
                    recognition.op("||")(
                        append(
                            object_("pointer", original["pointer"], "outcome", original["outcome"])
                        )
                    ),
                ),
            ),
        ),
        Assign(
            "projection",
            func.ops.ddo_digest(
                object_(
                    "text",
                    text_value,
                    "pieces",
                    pieces,
                    "items",
                    atoms,
                    "ancestors",
                    ancestors,
                    "recognition",
                    recognition,
                )
            ),
        ),
        Assign(
            "coordinate",
            object_(
                "document",
                document,
                "document_subject",
                literal("original-document:").concat(
                    func.ops.ddo_digest(object_("document", document))
                ),
                "section_pointer",
                section,
                "membership",
                membership,
                "projection",
                projection_id,
            ),
        ),
        ForQuery(
            ("selector",),
            select(selector_rows.c.value),
            (
                Perform(
                    func.ops.ddo_fields(
                        selector,
                        array(["projection"], type_=Text()),
                        array(["native_pointer", "page", "start", "end"], type_=Text()),
                    )
                ),
                _refuse(
                    or_(
                        selector["projection"].astext.is_distinct_from(projection_digest),
                        and_(
                            selector.has_key("native_pointer"),
                            or_(
                                func.jsonb_typeof(selector["native_pointer"]).is_distinct_from(
                                    "string"
                                ),
                                ~ancestor_selected,
                            ),
                        ),
                    ),
                    "original source selector differs from actual source projection/atom",
                    "P0001",
                ),
                ForQuery(
                    ("name",),
                    select(func.unnest(array(["page", "start", "end"], type_=Text()))),
                    (
                        _refuse(
                            and_(
                                selector.has_key(name),
                                or_(
                                    func.jsonb_typeof(selector[name]).is_distinct_from("number"),
                                    selector[name].astext.op("!~")("^(0|[1-9][0-9]*)$"),
                                ),
                            ),
                            "original source selector requires exact integer bounds",
                            "P0001",
                        ),
                    ),
                ),
                _refuse(
                    or_(
                        and_(
                            selector.has_key("page"),
                            cast(selector["page"].astext, BigInteger()) < 1,
                        ),
                        func.coalesce(cast(selector["start"].astext, BigInteger()), 0)
                        > func.coalesce(
                            cast(selector["end"].astext, BigInteger()), func.char_length(text_value)
                        ),
                        func.coalesce(
                            cast(selector["end"].astext, BigInteger()), func.char_length(text_value)
                        )
                        > func.char_length(text_value),
                    ),
                    "original source selector exceeds original coordinate bounds",
                    "P0001",
                ),
                Assign(
                    "selected",
                    selected.op("||")(
                        append(
                            func.jsonb_set(
                                selector,
                                array(["projection"], type_=Text()),
                                func.to_jsonb(projection_id),
                            )
                        )
                    ),
                ),
            ),
        ),
        Return(
            object_(
                "source",
                coordinate,
                "text",
                text_value,
                "pieces",
                pieces,
                "items",
                atoms,
                "ancestors",
                ancestors,
                "recognition",
                recognition,
                "selectors",
                selected,
            )
        ),
    )
    return _routine(
        "ddo_native_source_body",
        (
            Parameter("p_document", pg_type("text")),
            Parameter("p_section", pg_type("text")),
            Parameter("p_membership", pg_type("text")),
            Parameter("p_projection", pg_type("jsonb")),
            Parameter("p_projection_digest", pg_type("text")),
            Parameter("p_items", pg_type("jsonb")),
            Parameter("p_selectors", pg_type("jsonb")),
        ),
        steps,
        volatility="immutable",
        protected=False,
        locals_=(
            *(
                Local(name, pg_type("jsonb"))
                for name in (
                    "atom",
                    "original",
                    "piece",
                    "selector",
                    "cell",
                    "retained_cell",
                    "table_data",
                    "cells",
                    "coordinate",
                )
            ),
            Local("name", pg_type("text")),
            Local("pointers", _text_array_type(), array([], type_=Text())),
            *(
                Local(name, pg_type("jsonb"), _json("[]"))
                for name in ("atoms", "ancestors", "all_atoms", "pieces", "recognition", "selected")
            ),
            Local("projection", pg_type("text")),
            Local("text_value", pg_type("text"), projection["text"].astext),
            Local("previous", pg_type("int8"), literal(0)),
        ),
    )


def _text_array_type():
    from pglast import ast

    datatype = pg_type("text")
    datatype.arrayBounds = (ast.Integer(ival=-1),)
    return datatype


def _producing_request(target):
    tables = target.tables
    derivations, intents, requests = (
        tables[name]
        for name in ("ops.data_derivation", "ops.data_completion_intent", "ops.data_request")
    )
    publications, tasks, definitions = (
        tables[name]
        for name in ("ops.data_publication_receipt", "ops.task", "sem.data_operation_definition")
    )
    generations, runtimes = tables["ops.data_request_generation"], tables["sem.runtime_binding"]
    uses, demands, obligations = (
        tables[name] for name in ("ops.demand_use", "ops.data_demand", "ops.data_obligation")
    )
    episode_id = core_variable("p_derivation", Text())

    def episode(name):
        return _field("episode", derivations, name)

    def intent(name):
        return _field("intent", intents, name)

    def publication(name):
        return _field("publication", publications, name)

    def job(name):
        return _field("job", tasks, name)

    def request(name):
        return _field("request", requests, name)

    def definition(name):
        return _field("definition", definitions, name)

    profile = core_variable("profile", Text())
    binding, candidate = (core_variable(name, JSONB()) for name in ("binding", "candidate"))
    captured_selection = core_variable("captured", JSONB(), "selection")
    captured_profile = core_variable("captured", JSONB(), "execution_profile")
    selected = uses.alias("selected")
    demand, obligation = demands.alias("demand"), obligations.alias("obligation")
    capture_query = (
        select(
            selected.c.selection, demand.c.selection["execution_profile"].label("execution_profile")
        )
        .select_from(
            selected.join(demand, demand.c.id == selected.c.demand_id).join(
                obligation,
                and_(
                    obligation.c.id == selected.c.obligation_id,
                    obligation.c.demand_id == demand.c.id,
                ),
            )
        )
        .where(
            selected.c.request_id == episode("request_id"),
            selected.c.generation == episode("generation"),
            selected.c.fate.in_(("attached", "fulfilled")),
            or_(selected.c.derivation_id.is_(None), selected.c.derivation_id == episode("id")),
            demand.c.project_id == request("project_id"),
            demand.c.release_id == episode("release_id"),
            demand.c.selection["execution_profile"].astext == profile,
            obligation.c.operation_id == request("operation_id"),
            obligation.c.subject == request("subject"),
            obligation.c.original_source.is_not_distinct_from(request("original_source")),
            obligation.c.analyzed_scope == request("analyzed_scope"),
            selected.c.selection["inputs"].is_not_distinct_from(intent("payload")["inputs"]),
            selected.c.selection["support"].is_not_distinct_from(intent("payload")["support"]),
        )
        .order_by(selected.c.created_at, selected.c.id)
    )
    steps = (
        _load(
            "episode",
            derivations,
            derivations.c.id == episode_id,
            derivations.c.outcome == "success",
        ),
        _load(
            "publication",
            publications,
            publications.c.intent_id == episode("intent_id"),
            publications.c.derivation_id == episode("id"),
        ),
        _load(
            "intent",
            intents,
            intents.c.id == publication("intent_id"),
            intents.c.request_id == episode("request_id"),
            intents.c.generation == episode("generation"),
        ),
        _load("request", requests, requests.c.id == episode("request_id")),
        _load("job", tasks, tasks.c.id == episode("producer_task_id")),
        _load(
            "definition",
            definitions,
            definitions.c.release_id == episode("release_id"),
            definitions.c.operation_id == request("operation_id"),
        ),
        _refuse(
            or_(
                tuple_(
                    intent("producer_task_id"), intent("producer_attempt"), intent("runtime_id")
                ).is_distinct_from(
                    tuple_(
                        episode("producer_task_id"),
                        episode("producer_attempt"),
                        episode("runtime_id"),
                    )
                ),
                publication("publishing_task_id").is_distinct_from(episode("producer_task_id")),
                ~publication("publishing_attempt").between(
                    intent("producer_attempt"), job("attempt")
                ),
                tuple_(
                    job("data_request_id"), job("data_generation"), job("release_id")
                ).is_distinct_from(
                    tuple_(episode("request_id"), episode("generation"), episode("release_id"))
                ),
                job("attempt") < intent("producer_attempt"),
                func.nullif(intent("producer_holder"), "").is_(None),
                ~exists(
                    select(1)
                    .select_from(generations)
                    .where(
                        generations.c.request_id == episode("request_id"),
                        generations.c.generation == episode("generation"),
                        generations.c.task_id == episode("producer_task_id"),
                    )
                ),
                episode("recipe").is_distinct_from(definition("recipe")),
                request("recipe").is_distinct_from(episode("recipe")),
                intent("payload")["implementation_revision"].astext.is_distinct_from(
                    definition("implementation_revision")
                ),
                func.ops.ddo_completion_state(
                    core_variable("definition", Text()), intent("payload")["outcome"].astext
                ).is_distinct_from(episode("outcome")),
            ),
            "PDF original producer differs from sealed episode/intent/task fences",
        ),
        SelectInto(
            select(
                cast(func.convert_from(runtimes.c.manifest_bytes, "UTF8"), JSONB())[
                    "execution_profile"
                ].astext
            ).where(
                runtimes.c.release_id == episode("release_id"),
                runtimes.c.runtime_id == episode("runtime_id"),
            ),
            ("profile",),
            strict=True,
        ),
        _refuse(
            func.nullif(profile, "").is_(None),
            "PDF original producer lacks its admitted execution profile",
        ),
        ForQuery(
            ("captured",),
            capture_query,
            (
                Assign(
                    "candidate",
                    captured_selection.op("||")(
                        func.jsonb_build_object("execution_profile", captured_profile)
                    ),
                ),
                If(
                    binding.is_(None),
                    (Assign("binding", candidate),),
                    (
                        _refuse(
                            binding.op("-")("read_id").is_distinct_from(
                                candidate.op("-")("read_id")
                            ),
                            "PDF original producer binding is ambiguous in immutable admitted uses",
                        ),
                    ),
                ),
            ),
        ),
        _refuse(
            binding.is_(None), "PDF original producer lacks its full immutable admitted binding"
        ),
        *(
            Assign(("request", name), value)
            for name, value in (
                ("release_id", episode("release_id")),
                ("runtime_id", episode("runtime_id")),
                ("recipe", episode("recipe")),
                ("generation", episode("generation")),
                ("live_task_id", episode("producer_task_id")),
                ("binding", binding),
            )
        ),
        Return(core_variable("request", Text())),
    )
    return _routine(
        "ddo_pdf_producing_request",
        (Parameter("p_derivation", pg_type("text")),),
        steps,
        result=pg_type(str(requests.schema), requests.name),
        strict=True,
        locals_=(
            *(
                Local(name, relation)
                for name, relation in (
                    ("episode", derivations),
                    ("intent", intents),
                    ("request", requests),
                    ("publication", publications),
                    ("job", tasks),
                    ("definition", definitions),
                )
            ),
            Local("profile", pg_type("text")),
            Local("captured", pg_type("record")),
            Local("binding", pg_type("jsonb")),
            Local("candidate", pg_type("jsonb")),
        ),
    )


def _selected_read(target, *, observations):
    demands, reads, products = (
        target.tables[name]
        for name in ("ops.data_demand", "ops.data_demand_read", "kb.data_product")
    )
    payload = core_variable("p", JSONB())

    def demand(name):
        return _field("demand", demands, name)

    receipt, cut = (core_variable(name, JSONB()) for name in ("receipt", "cut"))
    receipt_function = (
        func.ops.ddo_pdf_observation_derivation_receipt
        if observations
        else func.ops.ddo_pdf_derivation_receipt
    )
    return _routine(
        "read_selected_pdf_observations" if observations else "read_selected_pdf_source",
        (Parameter("p_payload", pg_type("jsonb")),),
        (
            Perform(
                func.ops.ddo_fields(
                    payload,
                    array(
                        [
                            "project_id",
                            "demand_id",
                            "read_id",
                            "use_id",
                            "product_id",
                            "derivation_id",
                        ],
                        type_=Text(),
                    ),
                )
            ),
            _load(
                "demand",
                demands,
                demands.c.id == payload["demand_id"].astext,
                demands.c.project_id == payload["project_id"].astext,
            ),
            Assign(
                "cut",
                func.ops.ddo_require_selected_output(
                    *(
                        payload[name].astext
                        for name in (
                            "demand_id",
                            "read_id",
                            "use_id",
                            "product_id",
                            "derivation_id",
                        )
                    )
                ),
            ),
            _load(
                "boundary",
                reads,
                reads.c.id == payload["read_id"].astext,
                reads.c.demand_id == demand("id"),
            ),
            read_presentation_check(
                _field("boundary", reads, "scope"),
                _field("boundary", reads, "public_disclosure"),
            ),
            Assign(
                "receipt",
                receipt_function(
                    demand("project_id"),
                    payload["product_id"].astext,
                    payload["derivation_id"].astext,
                    literal(None),
                    core_variable("boundary", Text()),
                ),
            ),
            Return(
                func.jsonb_build_object(
                    "payload",
                    func.jsonb_build_object(
                        "receipt",
                        receipt,
                        "cut",
                        cut,
                        "original_source",
                        select(products.c.original_source)
                        .where(products.c.id == payload["product_id"].astext)
                        .scalar_subquery(),
                    ),
                )
            ),
        ),
        volatility="volatile",
        locals_=(
            Local("p", pg_type("jsonb"), core_variable("p_payload", JSONB())),
            Local("demand", demands),
            Local("boundary", reads),
            Local("receipt", pg_type("jsonb")),
            Local("cut", pg_type("jsonb")),
        ),
    )


def _observation_receipt(target):
    requests, derivations, intents, products, definitions, outputs, reads = (
        target.tables[name]
        for name in (
            "ops.data_request",
            "ops.data_derivation",
            "ops.data_completion_intent",
            "kb.data_product",
            "sem.data_operation_definition",
            "ops.data_derivation_output",
            "ops.data_demand_read",
        )
    )
    project, product_id, derivation_id, source = (
        core_variable(name, Text())
        for name in ("p_project", "p_product", "p_derivation", "p_source")
    )

    def producer(name):
        return _field("producer", requests, name)

    def derivation(name):
        return _field("derivation", derivations, name)

    def intent(name):
        return _field("intent", intents, name)

    def product(name):
        return _field("product", products, name)

    receipt, receipts, expected = (
        core_variable(name, JSONB()) for name in ("receipt", "receipts", "expected")
    )
    return _routine(
        "ddo_pdf_observation_derivation_receipt",
        (
            Parameter("p_project", pg_type("text")),
            Parameter("p_product", pg_type("text")),
            Parameter("p_derivation", pg_type("text")),
            Parameter("p_source", pg_type("text"), pg_literal(None)),
            Parameter("p_read", pg_type(str(reads.schema), reads.name), pg_literal(None)),
        ),
        (
            _refuse(
                ~func.ops.ddo_node_valid(
                    "episode", derivation_id, core_variable("p_read", Text()), type_=Boolean()
                ),
                "observation derivation support is not admitted at selected read",
            ),
            SelectInto(
                select(core_relation_row(derivations))
                .select_from(derivations.join(outputs, outputs.c.derivation_id == derivations.c.id))
                .where(
                    derivations.c.id == derivation_id,
                    outputs.c.product_id == product_id,
                    outputs.c.member_id.is_(None),
                ),
                ("derivation",),
                strict=True,
            ),
            Assign("producer", func.ops.ddo_pdf_producing_request(derivation("id"))),
            _refuse(
                or_(
                    producer("project_id").is_distinct_from(project),
                    and_(source.is_not(None), producer("original_source").is_distinct_from(source)),
                ),
                "observation producer is outside exact qualified selected source",
            ),
            Perform(func.ops.ddo_authorize_request(core_variable("producer", Text()))),
            _refuse(
                ~exists(
                    select(1)
                    .select_from(definitions)
                    .where(
                        definitions.c.release_id == derivation("release_id"),
                        definitions.c.operation_id == producer("operation_id"),
                        func.coalesce(definitions.c.command_class == "pdf", False),
                        definitions.c.support_contract["effects"][0]["name"].astext
                        == "retain_pdf_observations",
                    )
                ),
                "selected observation derivation is not an approved recognition command",
            ),
            Perform(func.ops.require_pdf_operation(producer("release_id"), "read_pdf_product")),
            _load("intent", intents, intents.c.id == derivation("intent_id")),
            _load(
                "product",
                products,
                products.c.id == product_id,
                products.c.project_id == project,
                products.c.original_source == producer("original_source"),
            ),
            Assign("receipts", intent("payload")["execution_evidence"]["pdf_observation_receipts"]),
            _refuse(
                or_(
                    func.jsonb_typeof(receipts).is_distinct_from("array"),
                    func.jsonb_array_length(receipts) != 1,
                ),
                "selected observations lack one actual native retention receipt",
            ),
            Assign("receipt", receipts[0]),
            _refuse(
                receipt["runtime_id"].astext.is_distinct_from(intent("runtime_id")),
                "selected observation receipt changes its original producing runtime",
            ),
            Assign(
                "expected",
                func.ops.pdf_observation_projection_for_request(
                    receipt,
                    intent("producer_task_id"),
                    intent("producer_attempt"),
                    intent("producer_holder"),
                    core_variable("producer", Text()),
                ),
            ),
            _refuse(
                or_(
                    func.data.ddo_json(product("canonical_body")).is_distinct_from(expected),
                    expected["document"].astext.is_distinct_from(producer("original_source")),
                ),
                "selected observation meaning differs from native retained evidence",
            ),
            Return(receipt),
        ),
        locals_=(
            Local("producer", requests),
            Local("derivation", derivations),
            Local("intent", intents),
            Local("product", products),
            *(Local(name, pg_type("jsonb")) for name in ("receipts", "receipt", "expected")),
        ),
    )


def _observation_source(target):
    requests, derivations, definitions, products, outputs = (
        target.tables[name]
        for name in (
            "ops.data_request",
            "ops.data_derivation",
            "sem.data_operation_definition",
            "kb.data_product",
            "ops.data_derivation_output",
        )
    )
    request_id, project, product_id, derivation_id = (
        core_variable(name, Text())
        for name in ("p_request", "p_project", "p_product", "p_derivation")
    )

    def consumer(name):
        return _field("consumer", requests, name)

    def producer(name):
        return _field("producer", requests, name)

    def derivation(name):
        return _field("derivation", derivations, name)

    def raw_product(name):
        return _field("raw_product", products, name)

    receipt, capture, raw_capture = (
        core_variable(name, JSONB()) for name in ("receipt", "capture", "raw_capture")
    )
    selected_inputs = _items(consumer("binding")["inputs"], "selected_inputs")
    selected_support = _items(consumer("binding")["support"], "selected_support")
    observed_inputs = _items(producer("binding")["inputs"], "producer_inputs")
    observed_episode = func.ops.ddo_single_input_support_episode(raw_capture)
    lineage = select(func.ops.ddo_single_input_support_episode(capture).label("id")).cte(
        "lineage", recursive=True
    )
    from .support_edges import support_edge_queries

    historical = union_all(
        *support_edge_queries(target, literal("episode"), lineage.c.id, "lineage")
    ).lateral("historical_edge")
    lineage = lineage.union(
        select(historical.c.child_id.label("id")).select_from(lineage.join(historical, true()))
    )
    candidate = products.alias("candidate")
    return _routine(
        "ddo_pdf_observation_source",
        tuple(
            Parameter(name, pg_type("text"))
            for name in ("p_request", "p_project", "p_product", "p_derivation")
        ),
        (
            _load(
                "consumer", requests, requests.c.id == request_id, requests.c.project_id == project
            ),
            Perform(func.ops.ddo_authorize_request(core_variable("consumer", Text()))),
            _refuse(
                or_(
                    ~exists(
                        select(1)
                        .select_from(selected_inputs)
                        .where(
                            case(
                                (
                                    and_(
                                        selected_inputs.c.value["role"].astext == "observations",
                                        selected_inputs.c.value["product_id"].astext == product_id,
                                        selected_inputs.c.value["member_id"].astext.is_(None),
                                    ),
                                    func.ops.ddo_single_input_support_episode(
                                        selected_inputs.c.value
                                    )
                                    == derivation_id,
                                ),
                                else_=False,
                            )
                        )
                    ),
                    ~exists(
                        select(1)
                        .select_from(selected_support)
                        .where(selected_support.c.value["derivation_id"].astext == derivation_id)
                    ),
                ),
                "observations are outside exact selected computational support",
            ),
            Assign(
                "receipt",
                func.ops.ddo_pdf_observation_derivation_receipt(
                    project, product_id, derivation_id, consumer("original_source")
                ),
            ),
            _load("derivation", derivations, derivations.c.id == derivation_id),
            Assign("producer", func.ops.ddo_pdf_producing_request(derivation("id"))),
            SelectInto(
                select(observed_inputs.c.value).where(
                    observed_inputs.c.value["role"].astext == "capture"
                ),
                ("raw_capture",),
                strict=True,
            ),
            Perform(
                func.ops.ddo_pdf_capture_source_for_request(
                    core_variable("producer", Text()),
                    project,
                    raw_capture["product_id"].astext,
                    observed_episode,
                )
            ),
            _refuse(
                ~exists(
                    select(1)
                    .select_from(
                        derivations.join(requests, requests.c.id == derivations.c.request_id).join(
                            definitions,
                            and_(
                                definitions.c.release_id == derivations.c.release_id,
                                definitions.c.operation_id == requests.c.operation_id,
                            ),
                        )
                    )
                    .where(
                        derivations.c.id == observed_episode,
                        definitions.c.support_contract["effects"][0]["name"].astext
                        == "publish_pdf_capture",
                    )
                ),
                "recognition input is not the exact qualified raw capture kind",
            ),
            _load("raw_product", products, products.c.id == raw_capture["product_id"].astext),
            SelectInto(
                select(selected_inputs.c.value).where(
                    selected_inputs.c.value["role"].astext == "capture"
                ),
                ("capture",),
                strict=True,
            ),
            Perform(
                func.ops.ddo_pdf_capture_source(
                    consumer("id"),
                    project,
                    capture["product_id"].astext,
                    func.ops.ddo_single_input_support_episode(capture),
                )
            ),
            _refuse(
                ~exists(
                    select(1)
                    .select_from(
                        lineage.join(outputs, outputs.c.derivation_id == lineage.c.id).join(
                            candidate, candidate.c.id == outputs.c.product_id
                        )
                    )
                    .where(
                        outputs.c.member_id.is_(None),
                        candidate.c.id == raw_product("id"),
                        candidate.c.kind_contract == raw_product("kind_contract"),
                        candidate.c.project_id == project,
                        candidate.c.original_source == consumer("original_source"),
                        func.ops.ddo_node_valid("episode", lineage.c.id, type_=Boolean()),
                    )
                ),
                "observation raw capture differs from qualified selected source lineage",
            ),
            Return(
                func.jsonb_build_object(
                    "receipt",
                    receipt,
                    "value",
                    select(func.data.ddo_json(products.c.canonical_body))
                    .where(products.c.id == product_id)
                    .scalar_subquery(),
                )
            ),
        ),
        locals_=(
            Local("consumer", requests),
            Local("derivation", derivations),
            Local("producer", requests),
            *(Local(name, pg_type("jsonb")) for name in ("receipt", "capture", "raw_capture")),
            Local("raw_product", products),
        ),
        access=NativeProgramAccess(purposes=("write",)),
    )


def source_admission_native_programs(
    target, *, capture_programs=()
) -> tuple[ProgramDeclaration, ...]:
    """The selected reader installs after its actual captured source providers."""

    selected_source = _selected_read(target, observations=False)
    return (
        _native_source_body(),
        _producing_request(target),
        _selected_read(target, observations=True),
        *capture_programs,
        selected_source,
        _observation_receipt(target),
        _observation_source(target),
    )


def source_admission_native_sql(target) -> str:
    """Render six source owners; installation integrates typed capture providers."""
    return native_sql_script(
        item.routine.render() for item in source_admission_native_programs(target)
    )
