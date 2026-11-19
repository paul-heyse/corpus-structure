"""Native family programs and selection from admitted operation declarations."""

from dataclasses import dataclass
from functools import lru_cache

from sqlalchemy import Boolean, and_, func, literal, select
from sqlalchemy.dialects.postgresql import JSONB


@dataclass(frozen=True)
class FamilyPrograms:
    family: str
    validator: str
    guards: tuple[str, ...]


@lru_cache(maxsize=8)
def registered_family_sources(model):
    """Retain each validity producer's own declarations for this authoring capture."""
    from .artifact_admission_native import artifact_admission_native_programs
    from .contextual_admission_native import contextual_admission_native_programs
    from .definition_admission_native import definition_admission_native_programs
    from .operation_event_native import operation_event_native_programs
    from .record_grade_native import record_grade_native_programs
    from .record_policy_completion_native import record_policy_completion_native_programs
    from .rich_admission_native import rich_admission_native_programs
    from .support_trust_native import support_trust_native_programs

    return (
        ("native/data-operation-record-grade-native.sql", record_grade_native_programs(model)),
        (
            "native/data-operation-record-policy-completion.sql",
            record_policy_completion_native_programs(model),
        ),
        ("native/data-operation-operation-event.sql", operation_event_native_programs(model)),
        (
            "native/data-operation-contextual-admission.sql",
            contextual_admission_native_programs(target_metadata=model),
        ),
        (
            "native/data-operation-definition-admission.sql",
            definition_admission_native_programs(target_metadata=model),
        ),
        (
            "native/data-operation-artifact-admission.sql",
            artifact_admission_native_programs(target_metadata=model),
        ),
        (
            "native/data-operation-rich-admission.sql",
            rich_admission_native_programs(target_metadata=model),
        ),
        ("native/demand-trust.sql", support_trust_native_programs(model)),
    )


@lru_cache(maxsize=8)
def family_programs(model) -> tuple[FamilyPrograms, ...]:
    from pglast.stream import RawStream

    from corpus_structure.schema.operation_declarations import vocabulary

    claims = {}
    for _, declarations in registered_family_sources(model):
        for program in declarations:
            for role in program.validity:
                grouped = claims.setdefault(role.family, {})
                grouped.setdefault(role.role, []).append(program)
    declared = vocabulary("ValidityFamily")
    provisional = {name for name, status in declared.statuses if status == "provisional"}
    ready = declared.members - provisional - {"none", "undetermined"} | {"conservative"}
    if claims.keys() != ready:
        raise ValueError("native validity programs differ from declared ready families")
    result = []
    for family, grouped in claims.items():
        validators = grouped.get("validator", ())
        if len(validators) != 1:
            raise ValueError(f"family {family} requires exactly one validator program")
        validator = validators[0].routine
        if (
            validator.schema != "ops"
            or validator.argument_types != ("text",)
            or RawStream()(validator.returns) not in {"bool", "boolean"}
        ):
            raise ValueError(f"family {family} validator requires text to boolean signature")
        guards = tuple(item.routine.name for item in grouped.get("completion_guard", ()))
        if family != "conservative" and not guards:
            raise ValueError(f"family {family} requires a completion guard")
        if len(guards) != len(set(guards)):
            raise ValueError(f"family {family} repeats a completion guard")
        result.append(FamilyPrograms(family, validator.name, guards))
    return tuple(result)


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


def family_validity(model, definitions, derivation):
    validators = family_programs(model)
    conservative = next(entry for entry in validators if entry.family == "conservative")
    return and_(
        *(
            ~definitions.c.validity_families.contains([entry.family])
            | func.coalesce(getattr(func.ops, entry.validator)(derivation), literal(False))
            for entry in validators
            if entry.family != "conservative"
        ),
        ~definitions.c.validity_conservative
        | func.coalesce(
            getattr(func.ops, conservative.validator)(derivation, type_=Boolean()),
            literal(False),
        ),
    )


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
