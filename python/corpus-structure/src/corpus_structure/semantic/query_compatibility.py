"""Release-owned named-query contracts and trusted installed implementation custody.

Acquisition is explicit I/O; preparation uses only supplied immutable bytes. Archived
Python is evidence, never an executable fallback for an unsupported named query.
"""

from __future__ import annotations

import json
import platform
from dataclasses import dataclass
from hashlib import sha256
from importlib.metadata import version
from pathlib import Path
from typing import TYPE_CHECKING, Any, Literal

from pydantic import BaseModel, ConfigDict, Field, JsonValue

from corpus_structure._query_custody import QUERY_SOURCES, SourceCustodyError, query_sources

from .identity import canonical_bytes
from .refusals import SemanticRefusal
from .types import PreparedArtifact, RegistryRow, ResolvedDependencies, SourceArtifact

if TYPE_CHECKING:
    from collections.abc import Mapping

    from corpus_structure.serve.protocol import DomainQuery

    from .types import PreparedRelease

MANIFEST = "operation/query-manifest.json"
PRODUCT = "query_bindings.json"
_ROOT = Path(__file__).resolve().parents[1]
# Owner-declared answer determinants, not a traversal of arbitrary Python imports.
_RUNTIME_SOURCES = QUERY_SOURCES


class QueryCompatibilityError(SemanticRefusal):
    """The selected named route has no supported trusted implementation binding."""

    def __init__(self, message: str, *, reason: str = "incompatible_query"):
        self.reason = reason
        super().__init__(message)


class _Strict(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid", strict=True)


class CompatibilityEntry(_Strict):
    query: str = Field(min_length=1)
    contract: str = Field(pattern=r"^[0-9a-f]{64}$")
    implementation: str = Field(pattern=r"^[0-9a-f]{64}$")
    evidence: str = Field(min_length=1)


class BundleDeclaration(_Strict):
    version: Literal[1] = 1
    meaning_revision: str = Field(default="1", min_length=1)
    sources: list[str] = Field(default_factory=list)
    compatibility: list[CompatibilityEntry] = Field(default_factory=list)


class QueryContract(_Strict):
    name: str = Field(min_length=1)
    version: str = Field(min_length=1)
    meaning_revision: str = Field(min_length=1)
    parameters: dict[str, JsonValue]
    results: dict[str, JsonValue]
    required_operations: list[str] = Field(default_factory=lambda: ["query"])

    @property
    def identity(self) -> str:
        return _digest(self.model_dump(mode="json"))


class QueryBindingReference(_Strict):
    release_id: str
    query: str
    version: str
    contract: str
    producing_implementation: str
    implementation: str
    compatibility: str


class QueryManifest(_Strict):
    version: Literal[1] = 1
    pack: str = Field(min_length=1)
    sources: dict[str, str]
    runtime: dict[str, str]
    implementation: str
    queries: list[QueryContract]


def _digest(value: Any) -> str:
    return sha256(canonical_bytes(value)).hexdigest()


@dataclass(frozen=True)
class InstalledQueries:
    pack: Path
    declaration: BundleDeclaration
    sources: tuple[SourceArtifact, ...]
    runtime: dict[str, str]

    @property
    def implementation(self) -> str:
        return _digest(
            {"sources": {s.name: s.digest for s in self.sources}, "runtime": self.runtime}
        )

    @property
    def plugin(self) -> bytes | None:
        return next((s.content for s in self.sources if s.name == "pack/queries.py"), None)


def installed_query_inputs(pack: Path) -> InstalledQueries:
    """Capture the explicit source bundle before importing any pack query code."""
    declaration_path = pack / "query-bundle.json"
    declaration_bytes = declaration_path.read_bytes() if declaration_path.is_file() else b"{}"
    declaration = BundleDeclaration.model_validate_json(declaration_bytes)
    sources = [
        SourceArtifact("runtime/" + name, (_ROOT / name).read_bytes()) for name in _RUNTIME_SOURCES
    ]
    sources.append(SourceArtifact("pack/query-bundle.json", declaration_bytes))
    paths = ["queries.py", *declaration.sources]
    if len(paths) != len(set(paths)):
        raise QueryCompatibilityError(
            "duplicate named-query bundle source", reason="invalid_query_bundle"
        )
    for name in paths:
        relative = Path(name)
        if relative.is_absolute() or ".." in relative.parts or relative.as_posix() != name:
            raise QueryCompatibilityError(
                "query sources must be explicit pack-relative paths", reason="invalid_query_bundle"
            )
        path = pack / relative
        if name == "queries.py" and not path.exists():
            continue
        if not path.resolve().is_relative_to(pack.resolve()):
            raise QueryCompatibilityError(
                "query source escapes its pack", reason="invalid_query_bundle"
            )
        sources.append(SourceArtifact("pack/" + name, path.read_bytes()))
    return InstalledQueries(
        pack,
        declaration,
        tuple(sources),
        {
            "python": platform.python_version(),
            "pydantic": version("pydantic"),
            "sqlalchemy": version("sqlalchemy"),
        },
    )


def _registry(installed: InstalledQueries):
    expected = {}
    for source in installed.sources:
        if source.name == "pack/query-bundle.json":
            continue
        root, relative = source.name.split("/", 1)
        path = (_ROOT if root == "runtime" else installed.pack) / relative
        expected[str(path.resolve())] = source.digest
    try:
        with query_sources(expected, pack=installed.pack):
            from corpus_structure.serve.queries import GENERIC
            from corpus_structure.serve.registry import build_registry

            return build_registry(
                GENERIC,
                installed.pack,
                plugin_source=installed.plugin,
                implementation=installed.implementation,
            )
    except SourceCustodyError as error:
        raise QueryCompatibilityError(str(error), reason="unavailable_query") from error


def _contract(query: DomainQuery, meaning_revision: str) -> QueryContract:
    return QueryContract(
        name=query.name,
        version=query.version,
        meaning_revision=meaning_revision,
        parameters=query.params.model_json_schema(mode="validation"),
        results=query.result.model_json_schema(mode="serialization"),
    )


def acquire_query_inputs(pack: Path) -> tuple[SourceArtifact, ...]:
    installed = installed_query_inputs(pack)
    registry = _registry(installed)
    manifest = QueryManifest(
        pack=pack.name,
        sources={s.name: s.digest for s in installed.sources},
        runtime=installed.runtime,
        implementation=installed.implementation,
        queries=[_contract(q, installed.declaration.meaning_revision) for q in registry.values()],
    )
    return (
        SourceArtifact(MANIFEST, canonical_bytes(manifest.model_dump(mode="json"))),
        *(SourceArtifact("operation/query-source/" + s.name, s.content) for s in installed.sources),
    )


def prepare_query_bindings(dependencies: ResolvedDependencies):
    """Compile bindings from explicit supplied bytes, without installed I/O or imports."""
    artifacts = {s.name: s for s in dependencies.artifacts}
    manifests = [
        s for s in dependencies.artifacts if s.name == MANIFEST or s.name.endswith("/" + MANIFEST)
    ]
    if not manifests:
        return None
    bindings = []
    rows = []
    for source in manifests:
        manifest = QueryManifest.model_validate_json(source.content)
        prefix = source.name.removesuffix(MANIFEST)
        expected = {prefix + "operation/query-source/" + name for name in manifest.sources}
        actual = {name for name in artifacts if name.startswith(prefix + "operation/query-source/")}
        if actual != expected or any(
            artifacts[prefix + "operation/query-source/" + name].digest != digest
            for name, digest in manifest.sources.items()
        ):
            raise QueryCompatibilityError(
                "query manifest source custody differs", reason="invalid_query_bundle"
            )
        if manifest.implementation != _digest(
            {"sources": manifest.sources, "runtime": manifest.runtime}
        ):
            raise QueryCompatibilityError(
                "query implementation identity differs", reason="invalid_query_bundle"
            )
        names = [q.name for q in manifest.queries]
        if len(names) != len(set(names)):
            raise QueryCompatibilityError(
                "ambiguous producing query contract", reason="ambiguous_query"
            )
        for query in manifest.queries:
            binding = {
                "pack": manifest.pack,
                "contract": query.identity,
                "implementation": manifest.implementation,
                "query": query.model_dump(mode="json"),
            }
            bindings.append(binding)
            rows.append(
                RegistryRow(
                    "query_binding", manifest.pack + "/" + query.name, canonical_bytes(binding)
                )
            )
    if len({r.name for r in rows}) != len(rows):
        raise QueryCompatibilityError(
            "ambiguous producing pack/query binding", reason="ambiguous_query"
        )
    return PreparedArtifact(PRODUCT, canonical_bytes({"version": 1, "bindings": bindings})), tuple(
        rows
    )


@dataclass(frozen=True)
class BoundQuery:
    release_id: str
    query: DomainQuery
    contract: str
    producing_implementation: str
    implementation: str
    compatibility: str
    definition: QueryContract

    @property
    def name(self) -> str:
        return self.definition.name

    @property
    def version(self) -> str:
        return self.definition.version

    @property
    def reference(self) -> QueryBindingReference:
        return QueryBindingReference(
            release_id=self.release_id,
            query=self.name,
            version=self.version,
            contract=self.contract,
            producing_implementation=self.producing_implementation,
            implementation=self.implementation,
            compatibility=self.compatibility,
        )

    def __getattr__(self, name: str):
        return getattr(self.query, name)


def open_query_registry(
    prepared: PreparedRelease, pack: Path, *, query_name: str | None = None
) -> Mapping[str, BoundQuery]:
    """Resolve release custody and compatibility before loading installed query code."""
    products = [a for a in prepared.artifacts if a.kind == PRODUCT]
    if len(products) != 1:
        raise QueryCompatibilityError(
            "completed release has no named-query binding; prepare/select a supported release",
            reason="unavailable_query",
        )
    product = json.loads(products[0].content)
    if product.get("version") != 1:
        raise QueryCompatibilityError(
            "unsupported named-query binding reader", reason="unavailable_query"
        )
    installed = installed_query_inputs(pack)
    producing = [
        b
        for b in product["bindings"]
        if b["pack"] == pack.name and (query_name is None or b["query"]["name"] == query_name)
    ]
    if not producing:
        raise QueryCompatibilityError(
            "release has no binding for this query pack", reason="unavailable_query"
        )
    resolved = {}
    for binding in producing:
        contract = QueryContract.model_validate(binding["query"])
        if contract.identity != binding["contract"] or contract.name in resolved:
            raise QueryCompatibilityError(
                "ambiguous or invalid producing query identity", reason="ambiguous_query"
            )
        matches = [
            entry
            for entry in installed.declaration.compatibility
            if entry.query == contract.name
            and entry.contract == binding["contract"]
            and entry.implementation == binding["implementation"]
        ]
        exact = installed.implementation == binding["implementation"]
        if len(matches) > 1:
            raise QueryCompatibilityError(
                "ambiguous trusted query compatibility entry", reason="ambiguous_query"
            )
        if not exact and not matches:
            raise QueryCompatibilityError(
                "installed query implementation is incompatible with producing release; "
                "select/rebuild a supported release",
                reason="incompatible_query",
            )
        if prepared.execution_model_id is not None:
            from .contracts import bound_execution_model

            for operation in contract.required_operations:
                bound_execution_model(prepared).require_operation(operation)
        compatibility = _digest(
            {
                "contract": binding["contract"],
                "producing_implementation": binding["implementation"],
                "implementation": installed.implementation,
                "entry": matches[0].model_dump() if matches else "exact",
            }
        )
        resolved[contract.name] = (binding, contract, compatibility, exact)
    registry = _registry(installed)
    out = {}
    for name, (binding, contract, compatibility, exact) in resolved.items():
        query = registry.get(name)
        if query is None:
            raise QueryCompatibilityError(
                "installed query is unavailable", reason="unavailable_query"
            )
        current = _contract(query, installed.declaration.meaning_revision)
        if (
            current.identity != contract.identity
            if exact
            else (current.parameters, current.results) != (contract.parameters, contract.results)
        ):
            raise QueryCompatibilityError(
                "installed query meaning/parameter/result contract differs",
                reason="incompatible_query",
            )
        out[name] = BoundQuery(
            prepared.release_id,
            query,
            binding["contract"],
            binding["implementation"],
            installed.implementation,
            compatibility,
            contract,
        )
    return out


def validate_query_token(query: BoundQuery, body: Mapping[str, Any]) -> None:
    if any(
        body.get(field) != value
        for field, value in {
            "query_contract": query.contract,
            "implementation": query.implementation,
            "compatibility": query.compatibility,
        }.items()
    ):
        raise QueryCompatibilityError(
            "continuation query implementation/compatibility binding differs"
        )
