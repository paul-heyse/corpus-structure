"""Closed privileged effect policy and independent release admission grants."""

from dataclasses import dataclass
from typing import Any
from typing import cast as typing_cast

from sqlalchemy import Boolean, Text, and_, cast, column, func, literal, or_, select
from sqlalchemy.dialects.postgresql import JSONB

from corpus_structure.schema.integrity import annotation_values, integrity_from_view, role_name

from .native_objects import INTERNAL_PROGRAM, NativeProgramAccess
from .native_program_registry import ProgramDeclaration


@dataclass(frozen=True)
class PrivilegedEffect:
    name: str
    purposes: tuple[str, ...]
    authorization: tuple[str, ...]
    idempotency: str
    fulfillment: str

    @property
    def contract(self):
        return dict(
            name=self.name,
            authorization=list(self.authorization),
            idempotency=self.idempotency,
            fulfillment=self.fulfillment,
        )


def privileged_effects(model=None):
    from corpus_structure.model.compiled import compiled_model, running_model

    compiled = running_model() if model is None else model
    if hasattr(compiled, "info"):
        compiled = compiled_model(
            {
                **compiled.info["physical_sources"],
                "linkml:types": compiled.info["physical_linkml_types"],
            }
        )
    view = compiled.view("operation-integrity-vocabularies.yaml")
    policy = integrity_from_view(view)
    enum = view.get_enum("PrivilegedEffect")
    if enum is None or annotation_values(enum).get("cs:openness") != "closed":
        raise ValueError("privileged effect policy requires its closed vocabulary")
    effects = []
    for name, member in typing_cast(dict[str, Any], enum.permissible_values).items():
        facts = annotation_values(member)
        purposes, authorization = facts.get("cs:purposes"), facts.get("cs:authorization")
        if (
            not isinstance(purposes, list)
            or not purposes
            or any(policy.purpose_role(purpose) is None for purpose in purposes)
            or not isinstance(authorization, list)
            or not authorization
            or any(not isinstance(value, str) or not value for value in authorization)
            or any(
                not isinstance(facts.get(key), str) or not facts[key]
                for key in ("cs:idempotency", "cs:fulfillment")
            )
        ):
            raise ValueError("privileged effect lacks owning purposes or contract: " + name)
        effects.append(
            PrivilegedEffect(
                name,
                tuple(purposes),
                tuple(authorization),
                facts["cs:idempotency"],
                facts["cs:fulfillment"],
            )
        )
    return tuple(effects)


def _json(value):
    from .identity import canonical_bytes

    return cast(literal(canonical_bytes(value).decode()), JSONB())


def effect_native_programs(model) -> tuple[ProgramDeclaration, ...]:
    from .native_program import (
        Block,
        ForQuery,
        If,
        Local,
        NativeRoutine,
        Parameter,
        Perform,
        Raise,
        SelectInto,
        core_relation_row,
        core_variable,
        pg_type,
    )

    definitions = model.tables["sem.data_operation_definition"]
    grants = model.tables["sem.data_operation_effect_grant"]
    fields = {
        field.name: core_variable("definition", field.type, field.name) for field in definitions.c
    }
    effect = core_variable("effect", Text())
    rows = (
        func.jsonb_array_elements(fields["support_contract"]["effects"])
        .table_valued(column("value", JSONB()))
        .render_derived(name="claimed_effect")
    )
    policies = privileged_effects(model)
    valid_claim = or_(
        *(
            and_(
                effect == policy.name,
                fields["profile"] == "command",
                fields["support_contract"]["capabilities"]["preparation"].astext
                == "native-publication",
                fields["support_contract"]["effects"] == _json([policy.contract]),
            )
            for policy in policies
        )
    )
    parameters = (
        Parameter("definition", pg_type("sem", "data_operation_definition")),
        Parameter("effect", pg_type("text")),
    )
    eligible = NativeRoutine(
        "ops",
        "ddo_privileged_effect_eligible",
        parameters=parameters,
        returns=pg_type("bool"),
        body=select(valid_claim),
        volatility="immutable",
        strict=True,
        search_path=("pg_catalog", "pg_temp"),
    )
    principal = func.coalesce(
        func.nullif(func.current_setting("role"), "none"), func.session_user()
    )
    from corpus_structure.model.compiled import compiled_model

    captured = compiled_model(
        {
            **model.info["physical_sources"],
            "linkml:types": model.info["physical_linkml_types"],
        }
    )
    role_policy = integrity_from_view(captured.view("operation-integrity-vocabularies.yaml"))
    authorized_principal = or_(
        *(
            and_(
                effect == policy.name,
                or_(
                    *(
                        func.pg_has_role(
                            principal,
                            role_policy.purpose_role(purpose),
                            "MEMBER",
                            type_=Boolean(),
                        )
                        for purpose in policy.purposes
                    )
                ),
            )
            for policy in policies
        )
    )
    admitted = (
        select(1)
        .select_from(grants.join(rows, grants.c.contract == rows.c.value))
        .where(
            grants.c.release_id == fields["release_id"],
            grants.c.operation_id == fields["operation_id"],
            grants.c.definition_identity == fields["definition_identity"],
            grants.c.effect == effect,
        )
        .exists()
    )
    admitted_program = NativeRoutine(
        "ops",
        "ddo_privileged_effect_admitted",
        parameters=parameters,
        returns=pg_type("bool"),
        body=select(
            and_(
                func.ops.ddo_privileged_effect_eligible(
                    core_variable("definition", JSONB()), effect
                ),
                admitted,
            )
        ),
        volatility="stable",
        strict=True,
        security_definer=True,
        search_path=("pg_catalog", "pg_temp"),
    )
    authorized_program = NativeRoutine(
        "ops",
        "ddo_privileged_effect_authorized",
        parameters=parameters,
        returns=pg_type("bool"),
        body=select(
            and_(
                func.ops.ddo_privileged_effect_admitted(
                    core_variable("definition", JSONB()), effect
                ),
                authorized_principal,
            )
        ),
        volatility="stable",
        strict=True,
        security_definer=True,
        search_path=("pg_catalog", "pg_temp"),
    )
    material = core_variable("material", JSONB())
    material_contract = core_variable("material", JSONB(), "support_contract")
    effect_contract = core_variable("effect_contract", JSONB())
    declared_effects = (
        func.jsonb_array_elements(material_contract["effects"])
        .table_valued(column("value", JSONB()))
        .render_derived(name="declared_effect")
    )
    live_authority = NativeRoutine(
        "ops",
        "ddo_require_completion_effect_authority",
        parameters=(Parameter("r", pg_type("ops", "data_request")),),
        returns=pg_type("void"),
        body=Block(
            (
                SelectInto(
                    select(core_relation_row(definitions))
                    .select_from(definitions)
                    .where(
                        definitions.c.release_id == core_variable("r", Text(), "release_id"),
                        definitions.c.operation_id == core_variable("r", Text(), "operation_id"),
                    ),
                    ("material",),
                    strict=True,
                ),
                ForQuery(
                    ("effect_contract",),
                    select(declared_effects.c.value).where(
                        declared_effects.c.value["name"].astext.in_(
                            tuple(policy.name for policy in policies)
                        )
                    ),
                    (
                        If(
                            ~func.coalesce(
                                func.ops.ddo_privileged_effect_authorized(
                                    material, effect_contract["name"].astext
                                ),
                                False,
                            ),
                            (
                                Raise(
                                    "completion effect lacks its current native purpose and admitted release grant",
                                    "42501",
                                ),
                            ),
                        ),
                    ),
                ),
                If(
                    func.jsonb_path_exists(
                        material_contract["effects"],
                        '$[*].authorization[*] ? (@ == "native-purpose:evaluate")',
                    ),
                    (Perform(func.ops.ddo_authorize("evaluator")),),
                ),
            ),
            (Local("material", definitions), Local("effect_contract", pg_type("jsonb"))),
        ),
        volatility="stable",
        strict=True,
        security_definer=True,
        search_path=("pg_catalog", "pg_temp"),
    )
    return (
        *(
            ProgramDeclaration(
                routine,
                source="data-operations:forward",
                owner=role_name("publisher"),
                access=INTERNAL_PROGRAM,
            )
            for routine in (eligible, admitted_program, authorized_program, live_authority)
        ),
        ProgramDeclaration(
            _effect_grant_admission(model),
            source="data-operations:forward",
            owner=role_name("publisher"),
            access=NativeProgramAccess(purposes=("admit",)),
        ),
    )


def effect_programs(model) -> tuple[str, ...]:
    """Render the capture/test projection of the typed effect programs."""
    return tuple(declaration.routine.render() for declaration in effect_native_programs(model))


def require_admitted_effect(model, request, name):
    """Authenticate a material grant independently of the current consumer's purpose."""
    definitions = model.tables["sem.data_operation_definition"]
    return (
        select(1)
        .select_from(definitions)
        .where(
            definitions.c.release_id == request("release_id"),
            definitions.c.operation_id == request("operation_id"),
            func.ops.ddo_privileged_effect_admitted(definitions.table_valued(), name),
        )
        .exists()
    )


@dataclass(frozen=True)
class ApprovedEffect:
    operation_id: str
    effect: str

    def __post_init__(self):
        if not self.operation_id or not self.effect:
            raise ValueError("effect approval requires an operation and effect")


def approved_effect_rows(prepared, model, approvals: tuple[ApprovedEffect, ...]):
    """Resolve explicit operator approvals independently of operation claims."""
    from .native_definition_projection import read_native_definition_projection

    projection = read_native_definition_projection(prepared, model=model)
    definitions = {record["operation_id"]: record for record in projection["operations"]}
    if len({(record.operation_id, record.effect) for record in approvals}) != len(approvals):
        raise ValueError("duplicate approved effect owner")
    grants = []
    for approval in approvals:
        definition = definitions.get(approval.operation_id)
        if definition is None:
            raise ValueError("approved effect owner is absent from the release")
        claims = [
            record
            for record in definition["support_contract"]["effects"]
            if record["name"] == approval.effect
        ]
        if len(claims) != 1:
            raise ValueError("approved effect has no exact released claim")
        grants.append(
            dict(
                operation_id=approval.operation_id,
                definition_identity=definition["definition"],
                effect=approval.effect,
                contract=claims[0],
            )
        )
    return grants


def admit_effect_grants(connection, prepared, model, approvals: tuple[ApprovedEffect, ...]):
    from sqlalchemy import bindparam

    grants = approved_effect_rows(prepared, model, approvals)
    return connection.scalar(
        select(func.sem.admit_data_operation_effect_grants(bindparam("payload", type_=JSONB()))),
        {"payload": dict(release_id=prepared.release_id, grants=grants)},
    )


def _effect_grant_admission(model):
    from sqlalchemy import not_
    from sqlalchemy.dialects.postgresql import insert

    from corpus_structure.schema.integrity import role_name

    from .native_program import (
        Block,
        ForQuery,
        If,
        Local,
        NativeRoutine,
        Parameter,
        Raise,
        Return,
        Sql,
        core_variable,
        pg_type,
    )

    payload = core_variable("payload", JSONB())
    grant = core_variable("approved", JSONB())
    definitions = model.tables["sem.data_operation_definition"]
    grants = model.tables["sem.data_operation_effect_grant"]
    rows = (
        func.jsonb_array_elements(payload["grants"])
        .table_valued(column("value", JSONB()))
        .render_derived(name="approved_effect")
    )
    principal = func.coalesce(
        func.nullif(func.current_setting("role"), "none"), func.session_user()
    )
    matching_definition = (
        select(1)
        .select_from(definitions)
        .where(
            definitions.c.release_id == payload["release_id"].astext,
            definitions.c.operation_id == grant["operation_id"].astext,
            definitions.c.definition_identity == grant["definition_identity"].astext,
            definitions.c.support_contract["effects"] == func.jsonb_build_array(grant["contract"]),
            grant["contract"]["name"].astext == grant["effect"].astext,
            func.ops.ddo_privileged_effect_eligible(
                definitions.table_valued(), grant["effect"].astext
            ),
        )
        .exists()
    )
    inserted = dict(
        release_id=payload["release_id"].astext,
        operation_id=grant["operation_id"].astext,
        definition_identity=grant["definition_identity"].astext,
        effect=grant["effect"].astext,
        contract=grant["contract"],
    )
    exact_grant = (
        select(1)
        .select_from(grants)
        .where(*(grants.c[name].is_not_distinct_from(value) for name, value in inserted.items()))
        .exists()
    )
    duplicate = (
        select(1)
        .select_from(rows)
        .group_by(rows.c.value["operation_id"], rows.c.value["effect"])
        .having(func.count() != 1)
        .exists()
    )
    steps = (
        If(
            ~func.pg_has_role(principal, role_name("admitter"), "MEMBER", type_=Boolean()),
            (Raise("effect grants require the native admission purpose", "42501"),),
        ),
        If(
            func.jsonb_typeof(payload["grants"]).is_distinct_from("array"),
            (Raise("effect approvals require an explicit array", "23514"),),
        ),
        If(duplicate, (Raise("duplicate approved effect owner", "23514"),)),
        ForQuery(
            ("approved",),
            select(rows.c.value),
            (
                If(
                    not_(matching_definition),
                    (Raise("effect approval differs from its exact admitted definition", "23514"),),
                ),
                Sql(insert(grants).values(**inserted).on_conflict_do_nothing()),
                If(
                    not_(exact_grant),
                    (Raise("effect grant changed under its admitted identity", "23514"),),
                ),
            ),
        ),
        Return(payload["release_id"].astext),
    )
    return NativeRoutine(
        "sem",
        "admit_data_operation_effect_grants",
        parameters=(Parameter("payload", pg_type("jsonb")),),
        returns=pg_type("text"),
        body=Block(steps, (Local("approved", pg_type("jsonb")),)),
        security_definer=True,
        search_path=("pg_catalog", "pg_temp"),
    )
