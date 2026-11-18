"""Pure preparation of qualified projection analysis from explicit retained inputs."""

from __future__ import annotations

import json
from dataclasses import asdict
from hashlib import sha256
from typing import Literal

from linkml_runtime.utils.schemaview import SchemaView
from pydantic import BaseModel, ConfigDict, JsonValue, TypeAdapter, ValidationError
from pydantic.dataclasses import dataclass

from corpus_structure.schema.physical import compile_physical

from .determinants import projection_analysis_runtime
from .identity import canonical_bytes
from .projection_analysis import ProjectionAnalysis, analyze_recipe
from .refusals import SemanticRefusal
from .types import (
    SEMANTIC_COMPILER_VERSION,
    PreparationError,
    PreparedArtifact,
    PreparedRelease,
    ResolvedDependencies,
    SourceArtifact,
    SourceBundle,
)

ARTIFACT = "projection_analysis.json"


@dataclass(frozen=True, config=ConfigDict(extra="forbid", strict=True))
class ProjectionEntry:
    family: str
    analysis: ProjectionAnalysis


@dataclass(frozen=True, config=ConfigDict(extra="forbid", strict=True))
class ProjectionAnalysisProduct:
    version: Literal["projection-analysis-3"]
    complete: bool
    projections: tuple[ProjectionEntry, ...]
    physical_id: str | None = None
    source_id: str | None = None
    unknowns: tuple[str, ...] = ()


_PRODUCT = TypeAdapter(ProjectionAnalysisProduct)


def read_projection_analysis(prepared: PreparedRelease) -> ProjectionAnalysisProduct | None:
    """Read this archive's product, never substitute analysis of installed sources."""
    products = [artifact for artifact in prepared.artifacts if artifact.kind == ARTIFACT]
    if not products:
        return None
    if len(products) != 1:
        raise SemanticRefusal("Projection analysis product is duplicated")
    try:
        value = _PRODUCT.validate_json(products[0].content)
    except ValidationError as exc:
        raise SemanticRefusal("Unsupported retained projection analysis product") from exc
    families = tuple(item.family for item in value.projections)
    if len(set(families)) != len(families) or any(
        item.analysis.profile != "companion-query-analysis-3" for item in value.projections
    ):
        raise SemanticRefusal("Unsupported retained projection analysis profile")
    if any(item.analysis.detail_status != "available" for item in value.projections):
        raise SemanticRefusal("Retained v3 projection analysis lacks occurrence detail")
    return value


def _projection_view(bundle: SourceBundle) -> SchemaView:
    """Resolve the declared native recipe closure, without domain-boundary annotations."""
    from corpus_structure.model.compiled import compiled_model

    return compiled_model({s.name: s.content for s in bundle.sources}).private_view(bundle.root)


def _unavailable(*unknowns: str) -> PreparedArtifact:
    return PreparedArtifact(
        ARTIFACT,
        canonical_bytes(
            dict(version="projection-analysis-3", complete=False, unknowns=unknowns, projections=[])
        ),
    )


def prepare_projection_analysis(dependencies: ResolvedDependencies) -> PreparedArtifact | None:
    from .companion_projection import FAMILIES, prepare_projection

    supplied = {source.name: source.content for source in dependencies.artifacts}
    from .pdf_domain import CONTRACT, PREFIX, PdfDomainContract

    if CONTRACT not in supplied and not any(name.startswith(PREFIX) for name in supplied):
        return None
    runtime = projection_analysis_runtime(dependencies)
    try:
        content = supplied[CONTRACT]
        names = [source["name"] for source in json.loads(content)["inputs"]]
        domain = PdfDomainContract(
            content, tuple(SourceArtifact(name, supplied[name]) for name in names)
        )
        captured = {source.name: source.content for source in domain.sources}
        logical = {
            name.removeprefix(PREFIX + "logical/").replace("_", "-"): content
            for name, content in captured.items()
            if name.startswith(PREFIX + "logical/")
        }
        linkml_types = logical["linkml:types"]
        physical = compile_physical(
            {
                name.removeprefix(PREFIX + "physical/"): content
                for name, content in captured.items()
                if name.startswith(PREFIX + "physical/")
            },
            linkml_types=linkml_types,
        )
        bundle = SourceBundle(
            "companion-projections",
            tuple(
                SourceArtifact(name, logical[name])
                for name in (
                    "companion-projections",
                    "pdf-products",
                    "pdf-observation-vocabulary",
                    "pdf-records",
                    "pdf-staging",
                )
            ),
        )
        view = _projection_view(bundle)
    except (KeyError, ValueError, TypeError) as error:
        return _unavailable("Unsupported retained projection closure: " + str(error))
    physical_id = physical.info["physical_model_id"]
    source_id = sha256(
        b"corpus-projection-analysis-sources-3\0"
        + canonical_bytes(
            {
                "recipe": {source.name: source.digest for source in bundle.sources},
                "physical_id": physical_id,
                "linkml_types_sha256": sha256(linkml_types).hexdigest(),
                "compiler_version": SEMANTIC_COMPILER_VERSION,
                "runtime": runtime,
            }
        )
    ).hexdigest()
    reports = []
    complete = True
    for family in FAMILIES:
        try:
            prepared = prepare_projection(
                view, family, projection_id="projection:" + source_id, physical=physical
            )
        except PreparationError as error:
            return _unavailable("Unsupported retained projection profile: " + str(error))
        analysis = analyze_recipe(prepared.recipe)
        complete = complete and not analysis.unknowns
        reports.append(dict(family=family, analysis=asdict(analysis)))
    return PreparedArtifact(
        ARTIFACT,
        canonical_bytes(
            dict(
                version="projection-analysis-3",
                physical_id=physical_id,
                source_id=source_id,
                complete=complete,
                projections=reports,
            )
        ),
    )


class ProjectionAnalysisChange(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    model_ref: str
    aspect: Literal[
        "presence",
        "source_context",
        "consumers",
        "output_origins",
        "output_types",
        "value_dependencies",
        "relational_sources",
        "relational_dependencies",
        "expressions",
        "relationships",
        "helpers",
        "logical_sources",
        "occurrences",
        "coverage",
    ]
    before: JsonValue
    after: JsonValue
    consumers: tuple[str, ...]


class ProjectionAnalysisComparison(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    version: Literal["projection-analysis-comparison-v1"] = "projection-analysis-comparison-v1"
    before_release: str
    after_release: str
    before_source_id: str | None
    after_source_id: str | None
    changes: tuple[ProjectionAnalysisChange, ...]
    unknowns: tuple[str, ...]
    complete: bool


def compare_retained_projection_analysis(
    before: PreparedRelease, after: PreparedRelease
) -> ProjectionAnalysisComparison:
    """Compare retained query facts, never data impact, execution or currentness."""
    products = (read_projection_analysis(before), read_projection_analysis(after))
    old, new = products
    unknowns = set()
    for side, product in zip(("before", "after"), products, strict=True):
        if product is None:
            unknowns.add(side + ": retained query analysis unavailable")
            continue
        unknowns.update(side + ": " + message for message in product.unknowns)
        for entry in product.projections:
            unknowns.update(
                side + ": projection:" + entry.family + ": " + message
                for message in entry.analysis.unknowns
            )
    entries = tuple(
        {entry.family: entry.analysis for entry in product.projections} if product else {}
        for product in products
    )
    changes = []

    def append(reference, aspect, prior, current, consumers=()):
        if prior != current:
            changes.append(
                ProjectionAnalysisChange(
                    model_ref=reference,
                    aspect=aspect,
                    before=json.loads(canonical_bytes(prior)),
                    after=json.loads(canonical_bytes(current)),
                    consumers=tuple(sorted(set(consumers))),
                )
            )

    def context(product):
        return (
            None
            if product is None
            else {"physical_id": product.physical_id, "source_id": product.source_id}
        )

    append("projection:context", "source_context", context(old), context(new))
    fields = (
        "consumers",
        "output_origins",
        "output_types",
        "value_dependencies",
        "relational_sources",
        "relational_dependencies",
        "expressions",
        "relationships",
        "helpers",
        "logical_sources",
        "occurrences",
    )
    for family in sorted(entries[0].keys() | entries[1].keys()):
        prior, current = (entry.get(family) for entry in entries)
        consumers = {
            consumer for entry in (prior, current) if entry for consumer in entry.consumers
        }
        if prior is None or current is None:
            append(
                "projection:" + family,
                "presence",
                asdict(prior) if prior else None,
                asdict(current) if current else None,
                consumers,
            )
            unknowns.add(
                "projection:" + family + ": addition or removal has no pairwise query comparison"
            )
            continue
        append(
            "projection:" + family,
            "source_context",
            {
                "projection_id": prior.projection_id,
                "profile": prior.profile,
                "library_version": prior.library_version,
            },
            {
                "projection_id": current.projection_id,
                "profile": current.profile,
                "library_version": current.library_version,
            },
            consumers,
        )
        prior_facts, current_facts = asdict(prior), asdict(current)
        for field in fields:
            append(
                "projection:" + family, field, prior_facts[field], current_facts[field], consumers
            )
        append(
            "projection:" + family,
            "coverage",
            {"unknowns": prior.unknowns, "detail_status": prior.detail_status},
            {"unknowns": current.unknowns, "detail_status": current.detail_status},
            consumers,
        )
    return ProjectionAnalysisComparison(
        before_release=before.release_id,
        after_release=after.release_id,
        before_source_id=old.source_id if old else None,
        after_source_id=new.source_id if new else None,
        changes=tuple(changes),
        unknowns=tuple(sorted(unknowns)),
        complete=bool(old and new and old.complete and new.complete and not unknowns),
    )
