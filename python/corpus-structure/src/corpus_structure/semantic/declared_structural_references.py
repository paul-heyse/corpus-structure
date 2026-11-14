"""Structural addresses over admitted semantic products, without physical task aliases."""

from __future__ import annotations

from typing import Annotated, Literal

from pydantic import Field, model_validator

from .data_operation_model import BoundRoleMember, json_context_meaning
from .identity import canonical_bytes
from .structural_base import StructuralValue

Nonempty = Annotated[str, Field(min_length=1)]
Digest = Annotated[str, Field(pattern=r"^[0-9a-f]{64}$")]


class DeclaredStructuralSource(StructuralValue):
    format: Literal["declared-native-source-v1"] = "declared-native-source-v1"
    source: Nonempty
    subject: Nonempty
    document: Nonempty
    projection_digest: Digest
    section_pointer: Nonempty
    membership: Literal["direct", "descendants"]
    project_id: Nonempty
    original_source: Nonempty
    analyzed_scope_meaning: Nonempty
    source_product: Nonempty
    source_member: Nonempty | None = None
    kind_contract: Nonempty

    @model_validator(mode="after")
    def exact_reference(self):
        if (
            self.source != canonical_bytes([self.source_product, self.source_member]).decode()
            or self.document != self.original_source
        ):
            raise ValueError("declared structural source differs from its complete native address")
        return self

    def matches_pin(self, pin):
        return self.model_dump(mode="json", exclude_none=True) == dict(pin)

    @property
    def coordinate(self):
        from .original_documents import original_document_subject

        return canonical_bytes(
            {
                "document": self.document,
                "document_subject": original_document_subject(self.document),
                "section_pointer": self.section_pointer,
                "membership": self.membership,
                "projection": self.projection_digest,
            }
        )


class DeclaredProductRef(StructuralValue):
    """One exact admitted whole product/member and its unchanged qualified context."""

    product_id: Nonempty
    member_id: Nonempty | None = None
    kind_contract: Nonempty
    project_id: Nonempty
    subject: Nonempty
    original_source: Nonempty | None
    analyzed_scope_meaning: Nonempty

    @classmethod
    def from_bound(cls, member: BoundRoleMember, *, project: str, **values):
        return cls(
            product_id=member.product,
            member_id=member.member,
            kind_contract=member.kind_contract,
            project_id=project,
            subject=member.subject,
            original_source=member.original_source,
            analyzed_scope_meaning=json_context_meaning(member.analyzed_scope).decode(),
            **values,
        )

    @property
    def context(self):
        return {
            "project_id": self.project_id,
            "subject": self.subject,
            "original_source": self.original_source,
            "analyzed_scope_meaning": self.analyzed_scope_meaning,
        }


class DeclaredContributionRef(DeclaredProductRef):
    contribution_id: Annotated[str, Field(pattern=r"^source-contribution:[0-9a-f]{64}$")]


class DeclaredStructuralRef(DeclaredProductRef):
    structural_id: Nonempty


class DeclaredComponentRef(DeclaredStructuralRef):
    component_id: Digest
    operation_id: Nonempty
    operation_version: Nonempty
    dependencies: tuple[Nonempty, ...] = Field(min_length=1)


class DeclaredRelationshipRef(DeclaredProductRef):
    edge_id: Nonempty
