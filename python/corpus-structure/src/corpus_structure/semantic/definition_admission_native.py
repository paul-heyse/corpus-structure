"""Compile exact component CPU-body proof and definition publication correspondence.

Component proof is shared by contextual applicability and other current consumers;
it does not depend on contextual numerical/source factory acquisition.
"""

from sqlalchemy import (
    Integer,
    MetaData,
    Text,
    cast,
    column,
    exists,
    func,
    literal,
    or_,
    select,
)
from sqlalchemy.dialects.postgresql import JSONB

from corpus_structure.schema.integrity import role_name

from .metadata import get_metadata
from .native_objects import INTERNAL_PROGRAM, native_privilege_sql, native_sql_script
from .native_program import (
    Assign,
    Block,
    CatchDependencyInvalidity,
    ForQuery,
    If,
    Local,
    NativeRoutine,
    Parameter,
    Perform,
    Raise,
    Return,
    SelectInto,
    column_type,
    core_relation_row,
    core_variable,
    pg_type,
)
from .native_program_registry import ProgramDeclaration, ProgramValidity
from .validity_programs import input_role, selected_family


def definition_admission_native_programs(
    *, target_metadata: MetaData | None = None
) -> tuple[ProgramDeclaration, ...]:
    model = get_metadata() if target_metadata is None else target_metadata
    definition = model.tables["sem.data_operation_definition"]
    request = model.tables["ops.data_request"]
    episode = model.tables["ops.data_derivation"]
    intent = model.tables["ops.data_completion_intent"]
    receipt = model.tables["ops.data_publication_receipt"]
    derivation_output = model.tables["ops.data_derivation_output"]
    kind = model.tables["sem.data_kind_contract"]

    def row(name, table, field=None):
        return core_variable(
            name, table.table_valued().type if field is None else table.c[field].type, field
        )

    def lookup(name, table, *conditions):
        return SelectInto(
            select(core_relation_row(table)).select_from(table).where(*conditions),
            (name,),
            strict=True,
        )

    def json(value):
        return cast(literal(value), JSONB())

    def field(value, key):
        return func.data.ddo_field(value, key, type_=JSONB())

    def plain(value):
        return func.data.ddo_json(value, type_=JSONB())

    def items(value, name):
        return (
            func.jsonb_array_elements(value)
            .table_valued(column("value", JSONB()))
            .render_derived(name=name)
        )

    def reject(condition, message):
        return If(condition, (Raise(message, "23514"),))

    def r(field=None):
        return row("r", request, field)

    def d(field):
        return row("definition", definition, field)

    def e(field=None):
        return row("episode", episode, field)

    def i(field=None):
        return row("intent", intent, field)

    selected = core_variable("selected_input", JSONB())
    completion = core_variable("completion", JSONB())
    output = core_variable("output", JSONB())
    actual = core_variable("actual", JSONB())
    basis = core_variable("basis", JSONB())
    source_pins = core_variable("source_pins", JSONB())
    original_source_row = core_variable("original_source_row", JSONB())
    result_field = core_variable("result_field", Text())
    output_role = core_variable("output_role", derivation_output.c.role.type)
    support = d("support_contract")
    factory = support["capabilities"]["prepared_factory"]
    request_parameters = (
        Parameter("r", pg_type(str(request.schema), request.name)),
        Parameter("completion", pg_type("jsonb")),
    )
    definition_lookup = lookup(
        "definition",
        definition,
        definition.c.release_id == r("release_id"),
        definition.c.operation_id == r("operation_id"),
    )
    programs: list[ProgramDeclaration] = []

    def add(name, parameters, steps=(), locals_=(), *, returns="void", query=None, validity=()):
        programs.append(
            ProgramDeclaration(
                NativeRoutine(
                    "ops",
                    name,
                    parameters=parameters,
                    returns=pg_type(returns),
                    body=Block(tuple(steps), tuple(locals_)) if query is None else query,
                    security_definer=query is None,
                    volatility="stable" if query is None else "immutable",
                    strict=query is not None,
                    search_path=("pg_catalog", "pg_temp"),
                ),
                source="data-operations:forward",
                owner=role_name("publisher"),
                access=INTERNAL_PROGRAM,
                validity=validity,
            )
        )

    context = field(selected, "context")
    product_id = field(selected, "product_id")[1].astext
    member_id = plain(field(selected, "member_id"))
    pairs = (
        ("product_id", product_id),
        ("member_id", member_id),
        ("kind_contract", field(selected, "kind_contract")[1].astext),
        *(
            (name, field(context, name)[1].astext)
            for name in ("project_id", "subject", "subject_definition")
        ),
        ("original_source", plain(field(context, "original_source"))),
        ("analyzed_scope_meaning", func.data.canonical_json(field(context, "analyzed_scope"))),
        ("reference", func.data.canonical_json(func.jsonb_build_array(product_id, member_id))),
    )
    add(
        "ddo_definition_source_reference",
        (Parameter("selected_input", pg_type("jsonb")),),
        returns="jsonb",
        query=select(
            func.jsonb_build_object(*(part for pair in pairs for part in pair), type_=JSONB())
        ),
    )

    references = items(plain(field(selected, "support")), "references_")
    original_sources = items(field(basis, "roles")[1], "original_sources_")
    add(
        "ddo_definition_component_basis",
        (Parameter("selected_input", pg_type("jsonb")),),
        (
            reject(
                or_(
                    field(selected, "member_id").is_distinct_from(json('["null"]')),
                    ~exists(
                        select(1)
                        .select_from(kind)
                        .where(
                            kind.c.kind_contract == field(selected, "kind_contract")[1].astext,
                            kind.c.kind
                            == "urn:corpus:structural:DeclaredDefinitionComponentsReport",
                        )
                    ),
                ),
                "contextual component source requires its exact whole native report kind",
            ),
            SelectInto(
                select(core_relation_row(episode))
                .select_from(
                    episode.join(
                        receipt,
                        (receipt.c.derivation_id == episode.c.id)
                        & (receipt.c.intent_id == episode.c.intent_id),
                    ).join(derivation_output, derivation_output.c.derivation_id == episode.c.id)
                )
                .where(
                    derivation_output.c.product_id == product_id,
                    derivation_output.c.member_id.is_(None),
                    derivation_output.c.multiplicity == 1,
                    episode.c.outcome == "success",
                    episode.c.id.in_(
                        select(references.c.value["derivation_id"].astext).where(
                            references.c.value["kind"].astext == "computation"
                        )
                    ),
                ),
                ("episode",),
                strict=True,
            ),
            SelectInto(
                select(derivation_output.c.role).where(
                    derivation_output.c.derivation_id == e("id"),
                    derivation_output.c.product_id == product_id,
                    derivation_output.c.member_id.is_(None),
                    derivation_output.c.multiplicity == 1,
                ),
                ("output_role",),
                strict=True,
            ),
            lookup("r", request, request.c.id == e("request_id")),
            lookup(
                "intent",
                intent,
                intent.c.id == e("intent_id"),
                intent.c.request_id == e("request_id"),
                intent.c.generation == e("generation"),
            ),
            *(
                Assign(("r", key), e(key))
                for key in ("release_id", "runtime_id", "recipe", "generation")
            ),
            Assign(
                ("r", "binding"),
                r("binding").op("||")(
                    func.jsonb_build_object(
                        "inputs",
                        i("payload")["inputs"],
                        "support",
                        i("payload")["support"],
                        type_=JSONB(),
                    )
                ),
            ),
            lookup(
                "definition",
                definition,
                definition.c.release_id == e("release_id"),
                definition.c.operation_id == r("operation_id"),
            ),
            reject(
                or_(
                    d("profile").is_distinct_from("derivation"),
                    support["effects"].is_distinct_from(json("[]")),
                    support["capabilities"]["forms"].is_distinct_from(json('["scalar"]')),
                    factory["source_digest"].astext.op("~")("^[0-9a-f]{64}$").is_not(True),
                ),
                "contextual component report lacks an actual captured scalar CPU producer",
            ),
            Assign("actual", func.ops.ddo_cpu_reply_output(r(), i("payload"), type_=JSONB())),
            reject(
                func.jsonb_typeof(support["result_fields"]).is_distinct_from("object"),
                "component source lacks its admitted exact result-field projection",
            ),
            If(
                support["result_fields"] != json("{}"),
                (
                    Assign("result_field", support["result_fields"][output_role].astext),
                    reject(
                        result_field.is_(None),
                        "component CPU reply lacks its admitted output projection",
                    ),
                    Assign("actual", field(actual, result_field)),
                ),
                (
                    reject(
                        or_(
                            func.jsonb_array_length(d("output_roles")) != 1,
                            d("output_roles")[0]["name"].astext.is_distinct_from(output_role),
                        ),
                        "component CPU reply requires its actual admitted single output contract",
                    ),
                ),
            ),
            reject(
                actual.is_distinct_from(field(selected, "body")),
                "component source body differs from its actual original CPU reply",
            ),
            Assign("basis", func.ops.ddo_cpu_input_basis(r(), type_=JSONB())),
            SelectInto(
                select(original_sources.c.value).where(
                    field(original_sources.c.value, "role")[1].astext == "source"
                ),
                ("original_source_row",),
                strict=True,
            ),
            Assign("source_pins", plain(field(field(selected, "body"), "sources_input"))),
            reject(
                or_(
                    func.jsonb_typeof(source_pins).is_distinct_from("array"),
                    func.jsonb_array_length(source_pins) != 1,
                    func.jsonb_strip_nulls(source_pins[0]).is_distinct_from(
                        func.jsonb_strip_nulls(
                            func.ops.ddo_definition_source_reference(original_source_row)
                        )
                    ),
                ),
                "component source report differs from its exact original selected source/header",
            ),
            Return(basis),
        ),
        (
            Local("episode", episode),
            Local("r", request),
            Local("intent", intent),
            Local("definition", definition),
            Local("output_role", column_type(derivation_output.c.role)),
            Local("result_field", pg_type("text")),
            Local("actual", pg_type("jsonb")),
            Local("basis", pg_type("jsonb")),
            Local("original_source_row", pg_type("jsonb")),
            Local("source_pins", pg_type("jsonb")),
        ),
        returns="jsonb",
    )

    add(
        "ddo_require_definition_producer",
        request_parameters,
        (
            definition_lookup,
            reject(
                or_(
                    ~selected_family(model, r("release_id"), r("operation_id"), "definition"),
                    func.nullif(factory["entrypoint"].astext, "").is_(None),
                    factory["source_digest"].astext.op("~")("^[0-9a-f]{64}$").is_not(True),
                    d("implementation_revision").like("implementation-slice:%").is_not(True),
                    d("profile").is_distinct_from("derivation"),
                    d("recipe").is_distinct_from(r("recipe")),
                    support["capabilities"]["forms"].is_distinct_from(json('["scalar"]')),
                    support["capabilities"]["preparation"].astext.is_distinct_from("resource"),
                    support["effects"].is_distinct_from(json("[]")),
                    func.jsonb_array_length(
                        func.coalesce(completion["execution_evidence"]["cpu_receipts"], json("[]"))
                    )
                    != func.coalesce(
                        cast(support["capabilities"]["cpu_receipts"].astext, Integer()), -1
                    ),
                    completion["implementation_revision"].astext.is_distinct_from(
                        d("implementation_revision")
                    ),
                ),
                "contextual applicability lacks its actual captured scalar producer",
            ),
        ),
        (Local("definition", definition),),
    )

    outputs = items(completion["outputs"], "outputs_")
    add(
        "ddo_require_definition_completion",
        request_parameters,
        (
            If(
                ~selected_family(model, r("release_id"), r("operation_id"), "definition"),
                (Return(),),
            ),
            Perform(func.ops.ddo_require_definition_producer(r(), completion)),
            Assign("actual", func.ops.ddo_cpu_reply_output(r(), completion, type_=JSONB())),
            ForQuery(
                ("output",),
                select(outputs.c.value),
                (
                    reject(
                        actual.is_distinct_from(
                            func.data.ddo_normalize(output["product"]["body"], type_=JSONB())
                        ),
                        "definition publication differs from its actual exact-input CPU reply",
                    ),
                ),
            ),
            If(
                input_role(model, r("release_id"), r("operation_id"), "query"),
                (Perform(func.ops.ddo_require_contextual_definition_lineage(r(), completion)),),
            ),
        ),
        (Local("output", pg_type("jsonb")), Local("actual", pg_type("jsonb"))),
        validity=(ProgramValidity("definition", "completion_guard"),),
    )

    episode_id = core_variable("episode_id", episode.c.id.type)
    add(
        "ddo_definition_dependencies_valid",
        (Parameter("episode_id", column_type(episode.c.id)),),
        (
            CatchDependencyInvalidity(
                (
                    lookup("episode", episode, episode.c.id == episode_id),
                    lookup("r", request, request.c.id == e("request_id")),
                    If(
                        ~selected_family(model, r("release_id"), r("operation_id"), "definition"),
                        (Return(literal(True)),),
                    ),
                    If(e("outcome") != "success", (Return(literal(False)),)),
                    lookup(
                        "intent",
                        intent,
                        intent.c.id == e("intent_id"),
                        intent.c.request_id == e("request_id"),
                        intent.c.generation == e("generation"),
                    ),
                    Assign("r", func.ops.ddo_require_episode_correspondence(e(), i())),
                    Return(literal(True)),
                ),
                (Return(literal(False)),),
            ),
        ),
        (Local("episode", episode), Local("r", request), Local("intent", intent)),
        returns="bool",
        validity=(ProgramValidity("definition", "validator"),),
    )
    return tuple(programs)


def definition_admission_native_sql(*, target_metadata: MetaData | None = None) -> str:
    """Render captured declarations and their existing private ACL projection."""
    return (
        native_sql_script(
            statement
            for declaration in definition_admission_native_programs(target_metadata=target_metadata)
            for statement in (
                declaration.routine.render(),
                native_privilege_sql(declaration.identity, "PUBLIC", grant=False),
            )
        )
        + "\n"
    )
