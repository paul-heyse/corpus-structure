"""Frozen exact original-source pins for explicitly declared cross-source roles.

These values select an authenticated product/member. They grant no authority by
construction; native acquisition validates custody, the projected reference and
producing support before exposing any matching row.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field

from .data_operation_json import json_bytes, json_loads
from .identity import canonical_bytes
from .selected_support import (
    AllAdmissibleAcquisition,
    ProducerOutputOccurrence,
    SelectedReadReference,
    SelectedSourceProof,
    SelectedSupportAcquisition,
    SourceReadBasis,
    SourceSetAcquisition,
)


def is_semantic_source_reference(record):
    return (
        isinstance(record, dict)
        and set(record) in ({"product_id"}, {"product_id", "member_id"})
        and all(type(value) is str and bool(value) for value in record.values())
    )


@dataclass(frozen=True)
class SourceSetEntry:
    project_id: str
    original_source: str | None
    subject: str
    analyzed_scope: bytes
    subject_definition: str = field(kw_only=True)
    product: str
    member: str | None
    source_reference: str
    reference: bytes

    def __post_init__(self) -> None:
        if (
            any(
                type(value) is not str
                for value in (
                    self.project_id,
                    self.subject,
                    self.subject_definition,
                    self.product,
                    self.source_reference,
                )
            )
            or type(self.reference) is not bytes
            or type(self.analyzed_scope) is not bytes
        ):
            raise TypeError("source-set custody and reference pins require immutable exact types")
        if self.original_source is not None and (
            type(self.original_source) is not str or not self.original_source
        ):
            raise TypeError(
                "source-set original source requires explicit null or a nonempty string"
            )
        if self.member is not None and type(self.member) is not str:
            raise TypeError("source-set member must be an original string identifier")
        raw = json.loads(self.reference)
        if not is_semantic_source_reference(raw):
            raise ValueError("source sets require exact semantic product/member references")
        from .data_product_reference import DataProductMemberReference, DataProductReference

        product = DataProductReference(raw["product_id"])
        reference = (
            DataProductMemberReference(product, raw["member_id"]) if "member_id" in raw else product
        )
        member = reference.member_id if isinstance(reference, DataProductMemberReference) else None
        identity = (
            reference.identity
            if isinstance(reference, DataProductMemberReference)
            else product.product_id
        )
        if (
            product.product_id != self.product
            or member != self.member
            or identity != self.source_reference
        ):
            raise ValueError("source-set semantic reference differs from its exact product/member")
        canonical = canonical_bytes(reference.values())
        if not all((self.project_id, self.subject, self.subject_definition, self.product)):
            raise ValueError("source-set entries require exact qualified original custody")
        if self.member is not None and not self.member:
            raise ValueError("source-set member is null or a nonempty original identifier")
        scope = json_loads(self.analyzed_scope)
        if not isinstance(scope, dict):
            raise ValueError("source-set scope must be a canonical JSON object")
        object.__setattr__(self, "analyzed_scope", json_bytes(scope))
        if canonical != self.reference:
            raise ValueError("source-set original reference must be canonical")

    @classmethod
    def from_semantic_source(cls, reference, *, context):
        from .data_product_reference import DataProductMemberReference, DataProductReference

        if isinstance(reference, DataProductMemberReference):
            product, member, identity = (
                reference.product.product_id,
                reference.member_id,
                reference.identity,
            )
        elif isinstance(reference, DataProductReference):
            product, member, identity = reference.product_id, None, reference.product_id
        else:
            raise TypeError(
                "source-set reference requires the existing semantic product/member type"
            )
        return cls(
            context.project_id,
            context.original_source,
            context.subject,
            context.analyzed_scope,
            product,
            member,
            identity,
            canonical_bytes(reference.values()),
            subject_definition=context.subject_definition,
        )

    def record(self) -> dict:
        return {
            "project_id": self.project_id,
            "original_source": self.original_source,
            "subject": self.subject,
            "subject_definition": self.subject_definition,
            "analyzed_scope": json_loads(self.analyzed_scope),
            "product": self.product,
            "member": self.member,
            "source_reference": self.source_reference,
            "reference": json.loads(self.reference),
        }


@dataclass(frozen=True)
class SelectedSourceSetEntry:
    entry: SourceSetEntry
    read: SelectedReadReference
    proof: SelectedSourceProof

    def __post_init__(self):
        if (self.entry.product, self.entry.member, self.entry.project_id) != (
            self.proof.product_id, self.proof.member_id, self.read.project_id
        ):
            raise ValueError("selected source proof differs from semantic entry/project")

    @classmethod
    def from_selected_header(cls, header, cut, *, anchor_use_id=None):
        from .data_operation_model import SubjectContext
        from .data_operation_support import ComputationalSupportReference
        from .data_product_reference import DataProductMemberReference, DataProductReference

        product = DataProductReference(header["product_id"])
        reference = product if header["member_id"] is None else DataProductMemberReference(
            product, header["member_id"]
        )
        entry = SourceSetEntry.from_semantic_source(reference, context=SubjectContext(
            cut.record["project_id"], header["subject"], header["original_source"],
            json_bytes(header["analyzed_scope"]), subject_definition=header["subject_definition"],
        ))
        return cls(entry, SelectedReadReference.from_cut(cut), SelectedSourceProof(
            anchor_use_id=header["use_id"] if anchor_use_id is None else anchor_use_id,
            product_id=header["product_id"], member_id=header["member_id"],
            support=ComputationalSupportReference(
                derivation_id=header["derivation_id"], admission_use_id=header["use_id"],
            ),
            output=ProducerOutputOccurrence(
                member_id=header["output_member_id"], role=header["role"],
                position=header["position"], multiplicity=header["multiplicity"],
            ),
        ))


@dataclass(frozen=True)
class FrozenSourceSet:
    name: str
    entries: tuple[SourceSetEntry, ...]
    acquisition: SourceSetAcquisition

    def __post_init__(self) -> None:
        if (
            type(self.name) is not str
            or type(self.entries) is not tuple
            or any(not isinstance(entry, SourceSetEntry) for entry in self.entries)
        ):
            raise TypeError("source sets require an immutable typed entry tuple")
        if not self.name:
            raise ValueError("source sets require an explicit name")
        identities = {(entry.product, entry.member) for entry in self.entries}
        if len(identities) != len(self.entries):
            raise ValueError("source sets require unique qualified product/member pins")

        if isinstance(self.acquisition, SelectedSupportAcquisition):
            acquired = {
                (proof.product_id, proof.member_id)
                for read in self.acquisition.reads for proof in read.proofs
            }
            if acquired != identities or any(
                read.selection.project_id != entry.project_id
                for read in self.acquisition.reads for proof in read.proofs
                for entry in self.entries
                if (entry.product, entry.member) == (proof.product_id, proof.member_id)
            ):
                raise ValueError("source acquisition differs from its exact semantic entries")
        elif not isinstance(self.acquisition, AllAdmissibleAcquisition):
            raise TypeError("source sets require explicit typed acquisition")

    @classmethod
    def unqualified(cls, name, entries):
        """Intentionally select all otherwise admissible producing support."""
        return cls(name, entries, AllAdmissibleAcquisition())

    @classmethod
    def from_selected(cls, name, selections):
        by_address, by_cut = {}, {}
        for selected in selections:
            address = selected.entry.product, selected.entry.member
            previous = by_address.setdefault(address, selected.entry)
            if previous != selected.entry:
                raise ValueError("selected source address has conflicting qualified context")
            read, proofs = by_cut.setdefault(selected.read.cut_id, (selected.read, []))
            if read != selected.read:
                raise ValueError("selected source cut has conflicting exact bytes")
            proofs.append(selected.proof)
        from .data_operation_json import json_bytes

        reads = tuple(
            SourceReadBasis(selection=read, proofs=tuple(sorted(
                proofs, key=lambda proof: json_bytes(proof.model_dump(mode="python"))
            )))
            for _, (read, proofs) in sorted(by_cut.items())
        )
        return cls(name, tuple(by_address.values()), SelectedSupportAcquisition(reads=reads))

    def semantic_record(self) -> list[dict]:
        return [entry.record() for entry in sorted(
            self.entries, key=lambda entry: (entry.product, entry.member or "")
        )]

    def record(self) -> dict:
        return {"entries": self.semantic_record(),
                "acquisition": self.acquisition.model_dump(mode="python")}


def source_sets_record(source_sets: tuple[FrozenSourceSet, ...]) -> dict:
    if len({scope.name for scope in source_sets}) != len(source_sets):
        raise ValueError("duplicate frozen source-set name")
    return {scope.name: scope.record() for scope in sorted(source_sets, key=lambda scope: scope.name)}


def source_sets_meaning(record: dict) -> dict:
    """Project semantic addresses only; acquisition/read metadata never salts requests."""
    return {name: scope["entries"] for name, scope in sorted(record.items())}


def read_source_sets(record: dict) -> tuple[FrozenSourceSet, ...]:
    from pydantic import TypeAdapter

    result = []
    for name, scope in sorted(record.items()):
        if not isinstance(scope, dict) or set(scope) != {"entries", "acquisition"}:
            raise ValueError("source set requires current entries/acquisition envelope")
        entries = tuple(SourceSetEntry(
            entry["project_id"], entry["original_source"], entry["subject"],
            json_bytes(entry["analyzed_scope"]), entry["product"], entry["member"],
            entry["source_reference"], canonical_bytes(entry["reference"]),
            subject_definition=entry["subject_definition"],
        ) for entry in scope["entries"])
        acquisition = TypeAdapter(SourceSetAcquisition).validate_python(scope["acquisition"])
        result.append(FrozenSourceSet(name, entries, acquisition))
    return tuple(result)


def source_proof_predicate(scope, relation):
    """Role-local SQL selection of the explicitly frozen producing occurrences."""
    from sqlalchemy import and_, false, or_, true
    from sqlalchemy.dialects.postgresql import JSONB
    from sqlalchemy import type_coerce

    acquisition = scope["acquisition"]
    if acquisition["kind"] == "all-admissible-support-v1":
        return true()
    evidence = type_coerce(relation.c.support_evidence, JSONB)
    return or_(false(), *(
        and_(
            relation.c.product == proof["product_id"],
            relation.c.member.is_not_distinct_from(proof["member_id"]),
            relation.c.support_references == [proof["support"]],
            evidence["producer_output"] == proof["output"],
        )
        for read in acquisition["reads"] for proof in read["proofs"]
    ))
