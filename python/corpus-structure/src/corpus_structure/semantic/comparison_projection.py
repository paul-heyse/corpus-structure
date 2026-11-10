"""Release-bound qualifier roles for scientific comparison, separate from fact identity."""

from __future__ import annotations

import json
from dataclasses import asdict
from functools import cached_property, lru_cache
from typing import Any, Literal, Never

from pydantic import ConfigDict, TypeAdapter
from pydantic.dataclasses import dataclass

from .identity import canonical_bytes
from .types import (
    READABLE_COMPILER_VERSIONS,
    SEMANTIC_COMPILER_VERSION,
    ClassDefinition,
    Diagnostic,
    PreparationError,
    PreparedRelease,
)

ARTIFACT = "comparison_projection.json"
ABI = "comparison-projection-1"


@dataclass(frozen=True, config=ConfigDict(extra="forbid"))
class QualifierReference:
    name: str
    iri: str
    role: Literal["context", "compared", "evidence"]


@dataclass(frozen=True, config=ConfigDict(extra="forbid"))
class QualificationProjection:
    class_name: str
    class_iri: str
    properties: tuple[QualifierReference, ...]


@dataclass(frozen=True, config=ConfigDict(extra="forbid"))
class PredicateProjection:
    class_name: str
    class_iri: str
    property_iri: str
    qualification_class: str
    compared: tuple[QualifierReference, ...]


@dataclass(frozen=True, config=ConfigDict(extra="forbid"))
class ComparisonProjection:
    abi: Literal["comparison-projection-1"]
    compiler_version: Literal["14", "15", "16", "17", "18", "19"]
    operation: Literal["scientific_policy"]
    default: Literal["non-provenance-qualification-is-context-v1"]
    qualifications: tuple[QualificationProjection, ...]
    predicates: tuple[PredicateProjection, ...]

    @cached_property
    def _qualifications(self):
        return {q.class_name: q for q in self.qualifications}

    @cached_property
    def _predicates(self):
        return {(p.class_name, p.property_iri): p for p in self.predicates}

    def partition(
        self,
        class_name: str,
        predicate: str,
        qualification_class: str,
        values: dict[str, Any],
    ) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
        """Project supplied values without changing, filling or canonicalizing them."""
        qualification = self._qualifications.get(qualification_class)
        if qualification is None:
            raise ValueError(f"comparison qualification is unavailable: {qualification_class}")
        properties = {p.name: p for p in qualification.properties}
        if unknown := values.keys() - properties.keys():
            raise ValueError(f"undeclared comparison qualification: {sorted(unknown)}")
        projection = self._predicates.get((class_name, predicate))
        compared = {(p.name, p.iri) for p in projection.compared} if projection else set()
        meaningful = {n: v for n, v in values.items() if properties[n].role != "evidence"}
        meaning = {n: v for n, v in meaningful.items() if (n, properties[n].iri) in compared}
        context = {n: v for n, v in meaningful.items() if n not in meaning}
        return meaningful, context, meaning


def _fail(location: str, message: str) -> Never:
    raise PreparationError((Diagnostic("comparison_projection", location, message),))


def compile_comparison_projection(
    definitions: tuple[ClassDefinition, ...],
    metadata: dict[tuple[str, str], dict[str, str]],
    qualification_class: str | None,
) -> ComparisonProjection:
    """Resolve legacy declaration syntax once, against its effective qualification scope."""
    classes = {d.name: d for d in definitions}
    qualifications = tuple(
        QualificationProjection(
            d.name,
            d.iri,
            tuple(
                QualifierReference(
                    p.name, p.iri, "evidence" if p.key_role == "provenance" else "context"
                )
                for p in d.properties
            ),
        )
        for d in definitions
        if d.name == "Qualification" or "Qualification" in d.ancestors
    )
    if qualification_class is None:
        # Standalone domain preparation precedes AgentClaim composition. A single
        # declared specialization is unambiguous; multiple scopes need that binding.
        specialized = [q.class_name for q in qualifications if q.class_name != "Qualification"]
        qualification_class = specialized[0] if len(specialized) == 1 else "Qualification"
    qualification = classes.get(qualification_class)
    properties = {p.name: p for p in qualification.properties} if qualification else {}
    projections = []
    for definition in definitions:
        for prop in definition.properties:
            annotations = metadata.get((definition.name, prop.iri), {})
            if not {"cs:qualifiers", "cs:identity_qualifiers"}.intersection(annotations):
                continue
            location = f"{definition.name}/{prop.name}/comparison"
            lists = []
            for key in ("cs:qualifiers", "cs:identity_qualifiers"):
                names = annotations.get(key, "").split()
                if len(names) != len(set(names)):
                    _fail(location, f"{key} repeats a qualification property")
                for name in names:
                    if name not in properties:
                        _fail(
                            location, f"{key} references unavailable qualification property {name}"
                        )
                    if properties[name].key_role == "provenance":
                        _fail(
                            location, f"{key} assigns evidence-only property {name} to comparison"
                        )
                lists.append(set(names))
            declared, identity = lists
            if identity - declared:
                _fail(location, "identity qualifiers must also be declared qualifiers")
            if qualification is None:
                # Empty lists introduce no selected qualification reference. The
                # recorded default covers this declaration until a scope exists.
                continue
            projections.append(
                PredicateProjection(
                    definition.name,
                    definition.iri,
                    prop.iri,
                    qualification.name if qualification else "",
                    tuple(
                        QualifierReference(p.name, p.iri, "compared")
                        for p in properties.values()
                        if p.name in declared - identity
                    ),
                )
            )
    return ComparisonProjection(
        ABI,
        SEMANTIC_COMPILER_VERSION,
        "scientific_policy",
        "non-provenance-qualification-is-context-v1",
        qualifications,
        tuple(projections),
    )


def projection_bytes(projection: ComparisonProjection) -> bytes:
    return canonical_bytes(asdict(projection))


@lru_cache(maxsize=32)
def _read_projection(
    content: bytes, definitions: tuple[ClassDefinition, ...]
) -> ComparisonProjection:
    # The artifact is a resolved product. Reading never consults installed source annotations.
    projection = TypeAdapter(ComparisonProjection).validate_json(content, strict=True)
    qualifications = {q.class_name: q for q in projection.qualifications}
    if len(qualifications) != len(projection.qualifications):
        raise ValueError("comparison repeats a qualification scope")
    classes = {d.name: d for d in definitions}
    expected_qualifications = {
        d.name for d in definitions if d.name == "Qualification" or "Qualification" in d.ancestors
    }
    if qualifications.keys() != expected_qualifications:
        raise ValueError("comparison qualification inventory differs from the release")
    for qualification in qualifications.values():
        definition = classes[qualification.class_name]
        if qualification.class_iri != definition.iri or qualification.properties != tuple(
            QualifierReference(
                p.name, p.iri, "evidence" if p.key_role == "provenance" else "context"
            )
            for p in definition.properties
        ):
            raise ValueError("comparison qualification fields differ from the release")
        if len({p.name for p in qualification.properties}) != len(qualification.properties):
            raise ValueError("comparison repeats a qualification property")
        if any(p.role == "compared" for p in qualification.properties):
            raise ValueError("comparison default qualification role differs")
    if len(projection._predicates) != len(projection.predicates):
        raise ValueError("comparison repeats a predicate projection")
    for predicate in projection.predicates:
        definition = classes.get(predicate.class_name)
        if (
            definition is None
            or predicate.class_iri != definition.iri
            or not any(p.iri == predicate.property_iri for p in definition.properties)
        ):
            raise ValueError("comparison predicate scope differs from the release")
        qualification = qualifications.get(predicate.qualification_class)
        if qualification is None:
            raise ValueError("comparison predicate has no qualification scope")
        properties = {(p.name, p.iri): p for p in qualification.properties}
        if len({p.name for p in predicate.compared}) != len(predicate.compared):
            raise ValueError("comparison repeats a compared property")
        if any(
            p.role != "compared"
            or (p.name, p.iri) not in properties
            or properties[p.name, p.iri].role == "evidence"
            for p in predicate.compared
        ):
            raise ValueError("comparison predicate property/scope/role differs")
    return projection


def comparison_projection(prepared: PreparedRelease):
    compiler = json.loads(prepared.manifest)["profile"]["compiler_version"]
    artifacts = [a for a in prepared.artifacts if a.kind == ARTIFACT]
    if compiler in READABLE_COMPILER_VERSIONS:
        if len(artifacts) != 1:
            raise ValueError(
                f"compiler-{compiler} comparison requires its exact resolved projection"
            )
        projection = _read_projection(artifacts[0].content, prepared.definitions)
        if projection.compiler_version != compiler:
            raise ValueError("comparison artifact compiler differs from its release")
        return projection
    raise ValueError(f"unsupported comparison projection compiler {compiler}")
