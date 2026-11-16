"""Reconstruct actual rich child inputs from the shared lossless CPU authority basis."""

from dataclasses import dataclass, field

from .data_operation_cpu_basis import CPUInputRole, cpu_input_basis
from .data_operation_identity import decode_semantic_value, semantic_value
from .data_operation_json import json_bytes
from .data_operation_model import SubjectContext
from .data_operation_support import read_support_references
from .identity import canonical_bytes
from .rich_knowledge_contracts import DdoRichSelectedMember


def _context(value):
    if set(value) != {
        "project_id",
        "subject",
        "subject_definition",
        "original_source",
        "analyzed_scope",
    }:
        raise ValueError("rich child context differs from its actual shared basis shape")
    return SubjectContext(
        value["project_id"],
        value["subject"],
        value["original_source"],
        json_bytes(value["analyzed_scope"]),
        subject_definition=value["subject_definition"],
    )


@dataclass(frozen=True)
class RichKernelInputs:
    recipe: str
    context: SubjectContext
    roles: tuple[CPUInputRole, ...]
    parameters: bytes = field(kw_only=True)
    replicate: str | None = field(kw_only=True)

    @classmethod
    def from_basis(cls, meaning: list):
        value = decode_semantic_value(meaning)
        if (
            not isinstance(value, dict)
            or set(value) != {"version", "recipe", "context", "roles", "parameters", "replicate"}
            or value["version"] != "cpu-input-basis-2"
        ):
            raise ValueError("rich computation requires the actual shared CPU input basis")
        roles = []
        for role in value["roles"]:
            if set(role) != {
                "role",
                "position",
                "multiplicity",
                "product_id",
                "member_id",
                "kind_contract",
                "context",
                "body",
                "support",
            }:
                raise ValueError("rich child input differs from the actual finite role shape")
            roles.append(
                CPUInputRole(
                    role=role["role"],
                    position=role["position"],
                    multiplicity=role["multiplicity"],
                    product_id=role["product_id"],
                    member_id=role["member_id"],
                    kind_contract=role["kind_contract"],
                    context=_context(role["context"]),
                    body=role["body"],
                    support=read_support_references(role["support"]),
                )
            )
        result = cls(
            value["recipe"],
            _context(value["context"]),
            tuple(roles),
            parameters=canonical_bytes(semantic_value(value["parameters"])),
            replicate=value["replicate"],
        )
        if result.basis() != meaning:
            raise ValueError(
                "rich child basis differs from the inputs actually reconstructed for computation"
            )
        return result

    def basis(self):
        return cpu_input_basis(
            self.recipe,
            self.context,
            self.roles,
            parameters=self.parameters,
            replicate=self.replicate,
        )

    def selected(self, role: str):
        return tuple(value for value in self.roles if value.role == role)

    def scalar(self, role: str):
        values = self.selected(role)
        if len(values) != 1 or values[0].multiplicity != 1 or values[0].member_id is not None:
            raise ValueError("rich computation requires one actual whole input: " + role)
        return values[0]

    @staticmethod
    def reference(role: CPUInputRole) -> DdoRichSelectedMember:
        return DdoRichSelectedMember(
            product_id=role.product_id,
            member_id=role.member_id,
            kind_contract=role.kind_contract,
            support_references=role.support,
        )
