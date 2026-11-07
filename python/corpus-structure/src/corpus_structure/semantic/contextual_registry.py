"""Immutable curator-supplied target descriptions, separate from attributed source quotations."""

from __future__ import annotations

from collections.abc import Sequence

from pydantic import BaseModel, ConfigDict, Field, model_validator

from corpus_structure.methods.contextual_embeddings import identity
from corpus_structure.semantic.contextual_retrieval import target_representation
from corpus_structure.semantic.structural_products import ExternalSourceRef, RetainedComponentRef


class RegistryTarget(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    target_id: str = Field(min_length=1)
    label: str = Field(min_length=1)
    description: str = Field(min_length=1)
    aliases: tuple[str, ...] = ()
    type_name: str | None = None
    parent: str | None = None
    scope: str = "global"
    effective_version: str | None = None


def registry_input(targets: Sequence[RegistryTarget]):
    if not targets or len({t.target_id for t in targets}) != len(targets):
        raise ValueError("curated registry needs distinct targets")
    ordered = tuple(sorted(targets, key=lambda t: t.target_id))
    registry_id = identity("curated-registry", [t.model_dump(mode="json") for t in ordered])
    representations = tuple(
        target_representation(
            source_binding=identity("curated-target", t.model_dump(mode="json")),
            **t.model_dump(mode="python"),
        )
        for t in ordered
    )
    return registry_id, representations


class ExtractedComponentTarget(BaseModel):
    """Located component description; native completion authenticates its original custody."""

    model_config = ConfigDict(frozen=True, extra="forbid")
    reference: RetainedComponentRef
    label: str = Field(min_length=1)
    description: str = Field(min_length=1)
    scope: str = Field(min_length=1)
    effective_version: str | None = None
    parent: str | None = None

    def authenticated_reference(self):
        return self.reference


def component_target_input(targets: Sequence[ExtractedComponentTarget]):
    """Prepare immutable representations without manufacturing curated source attribution.

    This checks the reference contract, not whether a database really contains that
    component. The owned Reader and native completion resolve it against original results.
    """
    if not targets:
        raise ValueError("component inventory requires retained target components")
    ordered = tuple(sorted(targets, key=lambda t: t.authenticated_reference().identity))
    refs = tuple(target.authenticated_reference() for target in ordered)
    if len({ref.component_id for ref in refs}) != len(refs):
        raise ValueError("component inventory contains duplicate target identities")
    inventory_source = identity(
        "definition-component-inventory", [t.model_dump(mode="json") for t in ordered]
    )
    representations = tuple(
        target_representation(
            ref.component_id,
            "definition-component:" + ref.identity,
            target.label,
            target.description,
            scope=target.scope,
            effective_version=target.effective_version,
            parent=target.parent,
        )
        for target, ref in zip(ordered, refs, strict=True)
    )
    return inventory_source, representations


class SectionHeadingTarget(BaseModel):
    """One native heading occurrence with every selected view citation."""

    model_config = ConfigDict(frozen=True, extra="forbid")
    target_id: str
    designator: str = Field(pattern=r"^[0-9]+(?:\.[0-9]+)+$")
    label: str = Field(min_length=1)
    pointer: str = Field(min_length=1)
    work_id: str = Field(min_length=1)
    scope: str = Field(min_length=1)
    effective_version: str | None = None
    citations: tuple[ExternalSourceRef, ...] = Field(min_length=1)

    @model_validator(mode="after")
    def physical_identity(self):
        physical = {(ref.native_content_digest, ref.native_product_key) for ref in self.citations}
        citations = [ref.identity for ref in self.citations]
        if len(physical) != 1 or citations != sorted(set(citations)):
            raise ValueError("heading citations must bind one physical item in stable order")
        (product,) = physical
        if self.target_id != identity(
            "section-heading", [*product, self.pointer, 0, len(self.label)]
        ):
            raise ValueError("heading identity differs from exact native item extent")
        return self


def section_target_input(sources, targets: Sequence[SectionHeadingTarget]):
    """Prepare target representations from Reader-authenticated heading occurrences."""
    ordered = tuple(sorted(targets, key=lambda target: target.target_id))
    registry = identity(
        "section-heading-inventory",
        [
            [s.model_dump(mode="json") for s in sources],
            [t.model_dump(mode="json") for t in ordered],
        ],
    )
    representations = tuple(
        target_representation(
            target.target_id,
            target.target_id,
            target.label,
            target.label,
            type_name="section-heading",
            scope=target.scope,
            effective_version=target.effective_version,
        )
        for target in ordered
    )
    meanings = {
        target.target_id: {"section_heading": target.model_dump(mode="json", exclude_none=True)}
        for target in ordered
    }
    return registry, representations, meanings
