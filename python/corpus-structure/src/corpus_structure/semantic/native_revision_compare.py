"""Compare current generated install products with immutable native revision evidence."""

from dataclasses import dataclass
from hashlib import sha256

from .identity import canonical_bytes
from .native_admission import PhysicalCatalogExpectations
from .native_objects import NativeIdentity
from .native_program_registry import ProgramManifest


@dataclass(frozen=True)
class NativeProgramDelta:
    head_revision: str
    object_count: int
    kernel_identity: str
    physical_id: str
    privilege_digest: str
    added: tuple[NativeIdentity, ...]
    changed: tuple[NativeIdentity, ...]
    retired: tuple[NativeIdentity, ...]
    privileges_changed: tuple[tuple[str, str], ...]
    descriptor_changes: tuple[str, ...]
    requires_catalog: bool

    @property
    def unchanged(self) -> bool:
        return not any(
            (
                self.added,
                self.changed,
                self.retired,
                self.privileges_changed,
                self.descriptor_changes,
                self.requires_catalog,
            )
        )


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


def compare_native_programs(installation, predecessor: str) -> NativeProgramDelta | None:
    """Compare captured declarations with authenticated frozen head statements."""
    from .alembic_privileges import declared_policies
    from .execution_admission import _revision_expectation
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
    frozen = load_native_state(expected.state[0], digest=expected.state[1])
    descriptor, _ = target_predecessor_descriptor(frozen)
    manifest = ProgramManifest.from_definitions(frozen)
    prerequisites = target_physical_prerequisites(None, installation)
    products = (*prerequisites, *target_program_definitions(None, installation))
    desired = ProgramManifest.from_definitions(products)
    before, after = dict(manifest.programs), dict(desired.programs)
    added = tuple(key for key in after if key not in before)
    retired = tuple(key for key in before if key not in after)
    changed = tuple(key for key in after if key in before and before[key] != after[key])
    policies = declared_policies(
        installation.metadata, ((item.identity.schema, item.grants) for item in products)
    )
    old_policies = {(item["kind"], item["name"]): item for item in descriptor.get("privileges", ())}
    new_policies = {(item["kind"], item["name"]): item for item in policies}
    privileges_changed = tuple(
        key
        for key in sorted(old_policies.keys() | new_policies.keys())
        if canonical_bytes(old_policies.get(key)) != canonical_bytes(new_policies.get(key))
    )
    old = {item.identity: item.statements for item in frozen}
    operation_descriptor = next(item for item in products if item.identity == OPERATION_DESCRIPTOR)
    descriptor_changes = []
    if operation_descriptor.install_sql != old.get(OPERATION_DESCRIPTOR):
        descriptor_changes.append(OPERATION_DESCRIPTOR.qualified)
    physical_id = installation.authoring_inputs.physical_id
    requires_catalog = (
        expected.physical_id != physical_id
        or descriptor.get("kernel_identity") != manifest.kernel_identity
    )
    if requires_catalog or added or changed or retired or privileges_changed:
        descriptor_changes.append(EXECUTION_DESCRIPTOR.qualified)
    else:
        installed = tuple(item for item in frozen if item.identity != EXECUTION_DESCRIPTOR)
        current = describe_native_admission(
            definition_sql(products),
            inputs=installation.authoring_inputs,
            base_descriptor=target_admission_descriptor(installation, installed),
            native_objects=installed,
            target_metadata=installation.metadata,
            physical_catalog=_observed_physical_catalog(descriptor),
        )
        (rendered,) = render_programs(
            (execution_descriptor_program(current),), registry_schemas=frozenset({"data"})
        )
        if rendered.declared_definition.install_sql != old.get(EXECUTION_DESCRIPTOR):
            descriptor_changes.append(EXECUTION_DESCRIPTOR.qualified)
    return NativeProgramDelta(
        predecessor,
        len(products) + 1,
        desired.kernel_identity,
        physical_id,
        sha256(canonical_bytes(policies)).hexdigest(),
        added,
        changed,
        retired,
        privileges_changed,
        tuple(descriptor_changes),
        requires_catalog,
    )
