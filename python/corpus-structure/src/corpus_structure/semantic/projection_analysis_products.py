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

from corpus_structure.schema.physical import compile_physical

from .contracts import retained_physical_sources
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
_PREFIX = "execution/implementation/"


@dataclass(frozen=True, config=ConfigDict(extra="forbid", strict=True))
class ProjectionEntry:
    family: str
    analysis: ProjectionAnalysis


@dataclass(frozen=True, config=ConfigDict(extra="forbid", strict=True))
class ProjectionAnalysisProduct:
    version: Literal["projection-analysis-2"]
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
        item.analysis.profile != "companion-query-analysis-2" for item in value.projections
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


def _unavailable(*unknowns: str) -> PreparedArtifact:
    return PreparedArtifact(
        ARTIFACT,
        canonical_bytes(
            dict(version="projection-analysis-2", complete=False, unknowns=unknowns, projections=[])
        ),
    )


def prepare_projection_analysis(dependencies: ResolvedDependencies) -> PreparedArtifact | None:
    from .companion_projection import FAMILIES, prepare_projection

    supplied = {source.name: source.content for source in dependencies.artifacts}
    name = _PREFIX + "capture/companion-projection-model.yaml"
    if name not in supplied:
        return None
    # Direct callers must not bypass captured/runtime qualification either.
    runtime = projection_analysis_runtime(dependencies)
    required = {
        "companion-projections": name,
        "pdf-products": "execution/schema/pdf_products",
        "pdf-records": _PREFIX + "pdf/record-model.yaml",
        "pdf-staging": _PREFIX + "pdf/staging-model.yaml",
    }
    types_name = _PREFIX + "unified/linkml-types.yaml"
    missing = sorted(
        {*required.values(), _PREFIX + "pdf/record-physical.yaml", types_name} - supplied.keys()
    )
    if missing:
        return _unavailable(
            *("Required retained projection source unavailable: " + item for item in missing)
        )
    linkml_types = supplied[types_name]
    try:
        physical = compile_physical(
            retained_physical_sources(
                {
                    name.removeprefix(_PREFIX): content
                    for name, content in supplied.items()
                    if name.startswith(_PREFIX)
                }
            ),
            linkml_types=linkml_types,
        )
    except ValueError as error:
        return _unavailable("Unsupported retained physical profile: " + str(error))
    physical_id = physical.info["physical_model_id"]
    bundle = SourceBundle(
        "companion-projections",
        tuple(SourceArtifact(alias, supplied[path]) for alias, path in required.items()),
    )
    view = _projection_view(bundle)
    source_id = sha256(
        b"corpus-projection-analysis-sources-2\0"
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
                version="projection-analysis-2",
                physical_id=physical_id,
                source_id=source_id,
                complete=complete,
                projections=reports,
            )
        ),
    )
