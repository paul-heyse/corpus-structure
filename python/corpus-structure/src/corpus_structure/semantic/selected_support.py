"""Exact selected-support acquisition values, distinct from semantic addresses.

These immutable selectors grant no authority. Native acquisition authenticates the
retained read, the selected anchor and the actual producing use/output occurrence.
"""

from __future__ import annotations

from typing import Annotated, Literal, Self

from pydantic import BaseModel, ConfigDict, Field, model_validator

from .data_operation_support import ComputationalSupportReference

Nonempty = Annotated[str, Field(min_length=1)]


class _SelectedValue(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class SelectedReadReference(_SelectedValue):
    project_id: Nonempty
    demand_id: Nonempty
    read_id: Nonempty
    release_id: Nonempty
    runtime_id: Nonempty
    cut_id: Nonempty
    cut_canonical_json: Nonempty

    @model_validator(mode="after")
    def exact_cut(self) -> Self:
        from .demand_results import CutSelection

        cut = CutSelection(self.cut_canonical_json.encode())
        if cut.identity != self.cut_id or any(
            cut.record[name] != getattr(self, name)
            for name in ("project_id", "demand_id", "read_id", "release_id", "runtime_id")
        ):
            raise ValueError("selected support differs from its exact native cut bytes")
        return self

    @classmethod
    def from_cut(cls, cut):
        return cls(
            **{name: cut.record[name] for name in (
                "project_id", "demand_id", "read_id", "release_id", "runtime_id"
            )},
            cut_id=cut.identity,
            cut_canonical_json=cut.content.decode(),
        )


class SelectedOutputRoot(_SelectedValue):
    product_id: Nonempty
    member_id: Nonempty | None = None
    use_id: Nonempty | None
    derivation_id: Nonempty


class ProducerOutputOccurrence(_SelectedValue):
    """The emitting slot, before any whole-product member projection."""

    member_id: Nonempty | None
    role: Nonempty
    position: Annotated[int, Field(strict=True, ge=0)]
    multiplicity: Annotated[int, Field(strict=True, ge=1)]


class SelectedSourceProof(_SelectedValue):
    anchor_use_id: Nonempty
    product_id: Nonempty
    member_id: Nonempty | None
    support: ComputationalSupportReference
    output: ProducerOutputOccurrence

    @model_validator(mode="after")
    def computational_member(self) -> Self:
        if self.support.admission_use_id is None:
            raise ValueError("selected source proof requires its actual producing use")
        if self.output.member_id is not None and self.output.member_id != self.member_id:
            raise ValueError("selected member differs from its emitting member output")
        return self


class SourceReadBasis(_SelectedValue):
    selection: SelectedReadReference
    proofs: Annotated[tuple[SelectedSourceProof, ...], Field(min_length=1)]

    @model_validator(mode="after")
    def unique_proofs(self) -> Self:
        if len(set(self.proofs)) != len(self.proofs):
            raise ValueError("source acquisition repeats a selected proof")
        return self


class SelectedSupportAcquisition(_SelectedValue):
    kind: Literal["selected-support-v1"] = "selected-support-v1"
    reads: tuple[SourceReadBasis, ...]

    @model_validator(mode="after")
    def unique_reads(self) -> Self:
        if len({read.selection.cut_id for read in self.reads}) != len(self.reads):
            raise ValueError("source acquisition repeats a selected cut")
        return self


class AllAdmissibleAcquisition(_SelectedValue):
    kind: Literal["all-admissible-support-v1"] = "all-admissible-support-v1"


type SourceSetAcquisition = Annotated[
    SelectedSupportAcquisition | AllAdmissibleAcquisition, Field(discriminator="kind")
]
