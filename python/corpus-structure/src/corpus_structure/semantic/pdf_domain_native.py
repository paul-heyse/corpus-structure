"""Native PDF correspondence over frozen domain actions and input custody."""

import json

from sqlalchemy import Boolean, Text, cast, column, func, literal, select
from sqlalchemy.dialects.postgresql import JSONB, insert

from corpus_structure.schema.integrity import role_name

from .identity import canonical_bytes
from .metadata import get_metadata
from .native_objects import (
    INTERNAL_PROGRAM,
    NativeProgramAccess,
    native_privilege_sql,
    native_sql_script,
)
from .native_program import (
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
    Sql,
    column_type,
    core_variable,
    pg_type,
)
from .native_program_registry import ProgramDeclaration
from .pdf_domain import CONTRACT, HELPER_CONTRACT, PREFIX, pdf_domain_sources
from .pdf_lowering import PRODUCER_IDENTITY_INPUTS


def pdf_domain_native_programs(
    *, sources=None, target_metadata=None
) -> tuple[ProgramDeclaration, ...]:
    model = get_metadata() if target_metadata is None else target_metadata
    captured = pdf_domain_sources(include_producer=False) if sources is None else sources
    native_facet = json.loads(
        next(source.content for source in captured if source.name == CONTRACT)
    )
    native_inputs = [
        item for item in native_facet.pop("inputs") if item["name"] not in PRODUCER_IDENTITY_INPUTS
    ]
    inputs = model.tables["sem.input"]
    definitions = model.tables["sem.data_operation_definition"]
    contracts = model.tables["sem.pdf_operation_contract"]
    finalization = model.tables["sem.release_finalization"]

    release = core_variable("p_release", inputs.c.release_id.type)
    name = core_variable("p_name", inputs.c.input_name.type)
    operation = core_variable("p_operation", contracts.c.operation_id.type)
    fresh = core_variable("p_new_release", Boolean())
    content = core_variable("content_", inputs.c.content.type)
    facet_digest = core_variable("facet_digest", inputs.c.content_digest.type)
    expected, facet, input_spec, action = (
        core_variable(name, JSONB()) for name in ("expected_", "facet", "input_", "action_value")
    )
    action_id = core_variable("action_id", Text())

    def items(value):
        return func.jsonb_array_elements(value).table_valued(column("value", JSONB()))

    expected_items = items(expected)
    retained_inputs = items(facet["inputs"])
    actions = func.jsonb_each(facet["actions"]).table_valued(
        column("key", Text()), column("value", JSONB())
    )
    support = definitions.c.support_contract
    asset = items(support["assets"]).c.value

    scope = (inputs.c.release_id == release, inputs.c.input_kind == "dependency")
    contract_scope = (*scope, inputs.c.input_name == CONTRACT)
    authenticated = func.encode(func.sha256(inputs.c.content), "hex") == inputs.c.content_digest
    document = cast(func.convert_from(inputs.c.content, "UTF8"), JSONB())

    def matches_native_basis(value):
        header = cast(literal(canonical_bytes(native_facet).decode()), JSONB())
        inventory = cast(literal(canonical_bytes(native_inputs).decode()), JSONB())
        return (value.op("-", return_type=JSONB())("inputs") == header) & value["inputs"].contains(
            inventory
        )

    contract_available = select(inputs.c.input_name).where(*contract_scope).exists()
    refusal = Raise("PDF domain contract differs", "23514")
    capability_refusal = Raise("PDF action/capability correspondence differs", "23514")
    release_parameter = Parameter("p_release", column_type(inputs.c.release_id))
    policy = ("pg_catalog", "pg_temp")

    read = NativeRoutine(
        "ops",
        "pdf_contract_input",
        parameters=(release_parameter, Parameter("p_name", column_type(inputs.c.input_name))),
        returns=column_type(inputs.c.content),
        volatility="stable",
        security_definer=True,
        search_path=policy,
        body=Block(
            (
                If(
                    ~contract_available,
                    (Raise("current PDF domain contract is required", "23514"),),
                ),
                SelectInto(
                    select(document.op("->", return_type=JSONB())("inputs")).where(
                        *contract_scope, matches_native_basis(document), authenticated
                    ),
                    ("expected_",),
                ),
                If(expected.is_(None), (refusal,)),
                SelectInto(
                    select(inputs.c.content).where(
                        *scope,
                        inputs.c.input_name == (literal(PREFIX) + name),
                        select(expected_items.c.value)
                        .where(
                            expected_items.c.value["name"].astext == inputs.c.input_name,
                            expected_items.c.value["sha256"].astext == inputs.c.content_digest,
                        )
                        .correlate(inputs)
                        .exists(),
                        authenticated,
                    ),
                    ("content_",),
                    strict=True,
                ),
                Return(content),
            ),
            (
                Local("content_", column_type(inputs.c.content)),
                Local("expected_", pg_type("jsonb")),
            ),
        ),
    )

    action_scope = (
        contracts.c.release_id == release,
        contracts.c.operation_id == action_id,
        contracts.c.contract_id == action_id,
        contracts.c.contract_digest == facet_digest,
    )
    supported = (
        select(definitions.c.release_id)
        .where(
            definitions.c.release_id == release,
            support["capabilities"]["preparation"].astext == "pdf-native",
            select(asset)
            .where(
                asset["reference"].astext == CONTRACT,
                asset["contract"].astext == HELPER_CONTRACT,
                asset["role"].astext == "native-pdf-helper-bindings",
                asset["content_digest"].astext == facet_digest,
            )
            .correlate(definitions)
            .exists(),
        )
        .exists()
    )
    admit = NativeRoutine(
        "sem",
        "admit_pdf_operation_contracts",
        parameters=(release_parameter, Parameter("p_new_release", pg_type("bool"))),
        returns=pg_type("void"),
        security_definer=True,
        search_path=policy,
        body=Block(
            (
                SelectInto(
                    select(document, inputs.c.content_digest).where(*contract_scope, authenticated),
                    ("facet", "facet_digest"),
                ),
                If(
                    ~core_variable("found", Boolean()),
                    (If(contract_available, (refusal,)), Return()),
                ),
                If(fresh & matches_native_basis(facet).is_distinct_from(True), (refusal,)),
                If(~supported, (capability_refusal,)),
                # Forward DATA authenticates retained facts under their own
                # manifest. Runtime reads require the current contract.
                ForQuery(
                    ("input_",),
                    select(retained_inputs.c.value),
                    (
                        If(
                            ~select(inputs.c.input_name)
                            .where(
                                *scope,
                                inputs.c.input_name == input_spec["name"].astext,
                                inputs.c.content_digest == input_spec["sha256"].astext,
                                authenticated,
                            )
                            .exists(),
                            (Raise("PDF domain input differs from retained contract", "23514"),),
                        ),
                    ),
                ),
                ForQuery(
                    ("action_id", "action_value"),
                    select(actions.c.key, actions.c.value),
                    (
                        If(
                            action["contract"]["id"].astext.is_distinct_from(action_id),
                            (Raise("PDF action contract identity differs", "23514"),),
                        ),
                        Sql(
                            insert(contracts)
                            .values(
                                {
                                    contracts.c.release_id: release,
                                    contracts.c.operation_id: action_id,
                                    contracts.c.contract_id: action_id,
                                    contracts.c.contract_digest: facet_digest,
                                }
                            )
                            .on_conflict_do_nothing()
                        ),
                        If(
                            ~select(contracts.c.contract_digest).where(*action_scope).exists(),
                            (Raise("PDF action changed under admitted release", "23514"),),
                        ),
                    ),
                ),
            ),
            (
                Local("facet", pg_type("jsonb")),
                Local("facet_digest", column_type(inputs.c.content_digest)),
                Local("input_", pg_type("jsonb")),
                Local("action_id", pg_type("text")),
                Local("action_value", pg_type("jsonb")),
            ),
        ),
    )

    require = NativeRoutine(
        "ops",
        "require_pdf_operation",
        parameters=(
            release_parameter,
            Parameter("p_operation", column_type(contracts.c.operation_id)),
        ),
        returns=pg_type("void"),
        volatility="stable",
        security_definer=True,
        search_path=policy,
        body=Block(
            (
                Perform(func.ops.ddo_require_release_facts(release)),
                If(
                    ~select(finalization.c.release_id)
                    .where(finalization.c.release_id == release)
                    .exists()
                    | ~select(contracts.c.operation_id)
                    .where(
                        contracts.c.release_id == release,
                        contracts.c.operation_id == operation,
                        contracts.c.contract_id == operation,
                        select(inputs.c.input_name)
                        .where(
                            *contract_scope,
                            inputs.c.content_digest == contracts.c.contract_digest,
                            matches_native_basis(document),
                            authenticated,
                        )
                        .correlate(contracts)
                        .exists(),
                    )
                    .exists(),
                    (capability_refusal,),
                ),
            ),
        ),
    )
    return (
        ProgramDeclaration(
            read, "authoring/pdf-domain.sql", role_name("publisher"), INTERNAL_PROGRAM
        ),
        ProgramDeclaration(
            admit, "authoring/pdf-domain.sql", role_name("publisher"), INTERNAL_PROGRAM
        ),
        ProgramDeclaration(
            require,
            "authoring/pdf-domain.sql",
            role_name("publisher"),
            NativeProgramAccess(purposes=("write", "read", "admit", "evaluate")),
        ),
    )


def pdf_domain_native_sql(*, sources=None, target_metadata=None) -> str:
    return (
        native_sql_script(
            statement
            for program in pdf_domain_native_programs(
                sources=sources, target_metadata=target_metadata
            )
            for statement in (
                program.routine.render(),
                native_privilege_sql(program.identity, "PUBLIC", grant=False),
                *(
                    native_privilege_sql(
                        program.identity, role, privilege.lower(), grant_option=option
                    )
                    for role, privilege, option in program.access.grants(program.owner)
                ),
            )
        )
        + "\n"
    )
