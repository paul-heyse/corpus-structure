"""Pure preparation of qualified projection analysis from explicit retained inputs."""

from __future__ import annotations

from dataclasses import asdict
from hashlib import sha256
from typing import Any, Literal

import yaml
from linkml_runtime.dumpers import json_dumper
from linkml_runtime.linkml_model.meta import SchemaDefinition
from linkml_runtime.loaders import yaml_loader
from linkml_runtime.utils.schemaview import SchemaView
from linkml_runtime.utils.yamlutils import DupCheckYamlLoader
from pydantic import ConfigDict, TypeAdapter, ValidationError
from pydantic.dataclasses import dataclass

from .identity import canonical_bytes
from .metadata import PHYSICAL_MODEL_ID, metadata, physical_sources_id
from .projection_analysis import ProjectionAnalysis, analyze_recipe
from .refusals import SemanticRefusal
from .types import (
    PreparedArtifact,
    PreparedRelease,
    ResolvedDependencies,
    SourceArtifact,
    SourceBundle,
)

ARTIFACT = "projection_analysis.json"
_PREFIX = "execution/implementation/"


@dataclass(frozen=True, config=ConfigDict(extra="forbid", strict=True))
class ProjectionEntry:
    family: str
    analysis: ProjectionAnalysis


@dataclass(frozen=True, config=ConfigDict(extra="forbid", strict=True))
class ProjectionAnalysisProduct:
    version: Literal["projection-analysis-1"]
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
        item.analysis.profile != "companion-query-analysis-1" for item in value.projections
    ):
        raise SemanticRefusal("Unsupported retained projection analysis profile")
    return value


def _projection_view(bundle: SourceBundle) -> SchemaView:
    """Resolve the declared native recipe closure, without domain-boundary annotations."""
    schemas: dict[str, SchemaDefinition] = {}
    for source in bundle.sources:
        schema = yaml_loader.load(
            yaml.load(source.content, Loader=DupCheckYamlLoader), SchemaDefinition
        )
        if not isinstance(schema, SchemaDefinition):
            raise ValueError("Retained projection source is not a SchemaDefinition")
        schemas[source.name] = schema
    for name, schema in schemas.items():
        for imported in schema.imports or ():
            if str(imported) not in schemas:
                raise ValueError(f"Retained projection import not supplied: {name}/{imported}")
    importmap: dict[str, dict[str, Any] | str] = {}
    for name, schema in schemas.items():
        value = json_dumper.to_dict(schema)
        if not isinstance(value, dict):
            raise ValueError("Retained projection source does not serialize as a mapping")
        importmap[name] = value
    view = SchemaView(
        schemas[bundle.root],
        importmap=importmap,
    )
    view.merge_imports()
    merged = view.schema
    if merged is None:
        raise ValueError("Retained projection closure is unavailable")
    merged.imports = []
    return SchemaView(merged)


def prepare_projection_analysis(dependencies: ResolvedDependencies) -> PreparedArtifact | None:
    from .companion_projection import FAMILIES, prepare_projection

    supplied = {source.name: source.content for source in dependencies.artifacts}
    name = _PREFIX + "capture/companion-projection-model.yaml"
    if name not in supplied:
        return None
    required = {
        "companion-projections": name,
        "pdf-products": "execution/schema/pdf_products",
        "pdf-records": _PREFIX + "pdf/record-model.yaml",
        "pdf-staging": _PREFIX + "pdf/staging-model.yaml",
    }
    missing = sorted(set(required.values()) - supplied.keys())
    physical_name = _PREFIX + "pdf/record-physical.yaml"
    if missing or physical_name not in supplied:
        return PreparedArtifact(
            ARTIFACT,
            canonical_bytes(
                dict(
                    version="projection-analysis-1",
                    complete=False,
                    unknowns=[
                        "Required retained projection source unavailable: " + item
                        for item in [*missing, physical_name]
                        if item not in supplied
                    ],
                    projections=[],
                )
            ),
        )
    physical_id = physical_sources_id(
        {
            "physical.yaml": supplied[physical_name],
            "pdf-records.yaml": supplied[required["pdf-records"]],
            "pdf-staging.yaml": supplied[required["pdf-staging"]],
        }
    )
    if physical_id != PHYSICAL_MODEL_ID:
        return PreparedArtifact(
            ARTIFACT,
            canonical_bytes(
                dict(
                    version="projection-analysis-1",
                    complete=False,
                    unknowns=["Unsupported retained physical profile: " + physical_id],
                    projections=[],
                )
            ),
        )
    bundle = SourceBundle(
        "companion-projections",
        tuple(SourceArtifact(alias, supplied[path]) for alias, path in required.items()),
    )
    view = _projection_view(bundle)
    source_id = sha256(
        b"corpus-projection-analysis-sources-1\0"
        + canonical_bytes({source.name: source.digest for source in bundle.sources})
    ).hexdigest()
    reports = []
    complete = True
    for family in FAMILIES:
        prepared = prepare_projection(
            view,
            family,
            projection_id="projection:" + source_id,
            physical=metadata,
            physical_id=physical_id,
        )
        analysis = analyze_recipe(prepared.recipe)
        complete = complete and not analysis.unknowns
        reports.append(dict(family=family, analysis=asdict(analysis)))
    return PreparedArtifact(
        ARTIFACT,
        canonical_bytes(
            dict(
                version="projection-analysis-1",
                physical_id=physical_id,
                source_id=source_id,
                complete=complete,
                projections=reports,
            )
        ),
    )
