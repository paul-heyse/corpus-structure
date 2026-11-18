"""Native family programs and selection from admitted operation declarations."""

from dataclasses import dataclass

from sqlalchemy import Boolean, and_, func, literal, select
from sqlalchemy.dialects.postgresql import JSONB


@dataclass(frozen=True)
class FamilyPrograms:
    family: str
    validator: str
    guards: tuple[str, ...]


FAMILY_PROGRAMS = (
    FamilyPrograms(
        "record-grade",
        "ddo_record_grade_dependencies_valid",
        ("ddo_require_record_grade_completion",),
    ),
    FamilyPrograms(
        "record-fit", "ddo_record_fit_dependencies_valid", ("ddo_require_record_fit_completion",)
    ),
    FamilyPrograms(
        "operation-event",
        "ddo_operation_event_dependencies_valid",
        ("ddo_require_operation_event_completion",),
    ),
    FamilyPrograms(
        "contextual", "ddo_contextual_dependencies_valid", ("ddo_require_contextual_completion",)
    ),
    FamilyPrograms(
        "definition", "ddo_definition_dependencies_valid", ("ddo_require_definition_completion",)
    ),
    FamilyPrograms(
        "artifact", "ddo_artifact_dependencies_valid", ("ddo_require_artifact_completion",)
    ),
    FamilyPrograms(
        "rich",
        "ddo_rich_admission_dependencies_valid",
        ("ddo_require_rich_preparation_completion", "ddo_require_rich_admission_completion"),
    ),
)


def selected_family(model, release, operation, family):
    definition = model.tables["sem.data_operation_definition"]
    return (
        select(1)
        .select_from(definition)
        .where(
            definition.c.release_id == release,
            definition.c.operation_id == operation,
            definition.c.validity_families.contains([family]),
        )
        .exists()
    )


def family_validity(definitions, derivation):
    return and_(
        *(
            ~definitions.c.validity_families.contains([entry.family])
            | func.coalesce(getattr(func.ops, entry.validator)(derivation), literal(False))
            for entry in FAMILY_PROGRAMS
        ),
        ~definitions.c.validity_conservative
        | func.coalesce(
            func.ops.ddo_conservative_dependencies_valid(derivation, type_=Boolean()),
            literal(False),
        ),
    )


def validate_family_programs(statements):
    """Require each ready declared family to have one exact native validator."""
    from pglast import ast
    from pglast.stream import RawStream

    from corpus_structure.schema.operation_declarations import vocabulary

    declared = vocabulary("ValidityFamily")
    provisional = {name for name, status in declared.statuses if status == "provisional"}
    ready = declared.members - provisional - {"none", "undetermined"}
    families = [entry.family for entry in FAMILY_PROGRAMS]
    if len(set(families)) != len(families) or set(families) != ready:
        raise ValueError("native validity programs differ from declared ready families")
    functions = {}
    for raw in statements:
        statement = raw.stmt
        if isinstance(statement, ast.CreateFunctionStmt):
            name = tuple(part.sval for part in statement.funcname or ())
            functions.setdefault(name, []).append(statement)
    for entry in FAMILY_PROGRAMS:
        validators = functions.get(("ops", entry.validator), ())
        if len(validators) != 1:
            raise ValueError(f"family {entry.family} requires exactly one validator program")
        validator = validators[0]
        arguments = tuple(
            RawStream()(parameter.argType) for parameter in validator.parameters or ()
        )
        if (
            arguments != ("text",)
            or validator.returnType is None
            or RawStream()(validator.returnType) not in {"bool", "boolean"}
        ):
            raise ValueError(f"family {entry.family} validator requires text to boolean signature")
        for guard in entry.guards:
            if len(functions.get(("ops", guard), ())) != 1:
                raise ValueError(f"family {entry.family} requires exactly one guard {guard}")


def operation_field(model, release, operation, field):
    definition = model.tables["sem.data_operation_definition"]
    return (
        select(definition.c[field])
        .where(
            definition.c.release_id == release,
            definition.c.operation_id == operation,
        )
        .scalar_subquery()
    )


def input_role(model, release, operation, role):
    return operation_field(model, release, operation, "input_roles").contains(
        func.jsonb_build_array(func.jsonb_build_object("name", role), type_=JSONB())
    )
