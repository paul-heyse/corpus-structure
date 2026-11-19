"""Compare current generated install products with immutable native revision evidence."""

from dataclasses import dataclass

from .native_admission import PhysicalCatalogExpectations
from .native_program_registry import ProgramManifest


@dataclass(frozen=True)
class UnchangedNativePrograms:
    head_revision: str
    object_count: int
    kernel_identity: str


def _observed_physical_catalog(descriptor: dict) -> PhysicalCatalogExpectations:
    generated = {}
    defaults = {}
    for table in descriptor["tables"]:
        name = table["relation"]
        generated[name] = {
            column["name"]: column["default"] for column in table["columns"] if column["generated"]
        }
        defaults[name] = {
            column["name"]: column["default"]
            for column in table["columns"]
            if not column["generated"] and column["default"] is not None
        }
    return PhysicalCatalogExpectations(tuple(descriptor["indexes"]), generated, defaults)


def unchanged_native_programs(installation, predecessor: str) -> UnchangedNativePrograms | None:
    """Compare exact DDL and privileges before acquiring an authoring connection."""
    from .execution_admission import _revision_expectation
    from .identity import canonical_bytes
    from .migrations import ALEMBIC_DIR, head_revision
    from .native_admission import describe_native_admission, execution_descriptor_program
    from .native_authoring import definition_sql, load_native_state
    from .native_program_registry import EXECUTION_DESCRIPTOR, OPERATION_DESCRIPTOR, render_programs
    from .target_installation import (
        target_admission_descriptor,
        target_physical_prerequisites,
        target_predecessor_descriptor,
        target_program_definitions,
    )

    if predecessor != head_revision():
        return None
    expected = _revision_expectation(ALEMBIC_DIR / "versions", predecessor)
    if expected.physical_id != installation.authoring_inputs.physical_id:
        return None
    frozen = load_native_state(expected.state[0], digest=expected.state[1])
    descriptor, _ = target_predecessor_descriptor(frozen)
    manifest = ProgramManifest.from_definitions(frozen)
    if descriptor.get("kernel_identity") != manifest.kernel_identity:
        return None
    prerequisites = target_physical_prerequisites(None, installation)
    products = (*prerequisites, *target_program_definitions(None, installation))
    if ProgramManifest.from_definitions(products) != manifest:
        return None

    original_operation_descriptor = next(
        item for item in frozen if item.identity == OPERATION_DESCRIPTOR
    )
    operation_descriptor = next(item for item in products if item.identity == OPERATION_DESCRIPTOR)
    if operation_descriptor.install_sql != original_operation_descriptor.statements:
        return None
    installed = tuple(item for item in frozen if item.identity != EXECUTION_DESCRIPTOR)
    current = describe_native_admission(
        definition_sql(products),
        inputs=installation.authoring_inputs,
        base_descriptor=target_admission_descriptor(installation, installed),
        native_objects=installed,
        target_metadata=installation.metadata,
        physical_catalog=_observed_physical_catalog(descriptor),
    )
    if canonical_bytes(current) != canonical_bytes(descriptor):
        return None
    (current_descriptor,) = render_programs(
        (execution_descriptor_program(current),), registry_schemas=frozenset({"data"})
    )
    original_descriptor = next(item for item in frozen if item.identity == EXECUTION_DESCRIPTOR)
    if current_descriptor.declared_definition.install_sql != original_descriptor.statements:
        return None
    return UnchangedNativePrograms(predecessor, len(frozen), manifest.kernel_identity)
