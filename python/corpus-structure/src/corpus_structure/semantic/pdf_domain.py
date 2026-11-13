"""PDF-owned contract projection for native document data operations.

This projects existing declared producer/reader actions; it does not recreate a
legacy execution model or infer permissions from an operation-name prefix.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from functools import cache
from pathlib import Path
from typing import Any

from .identity import canonical_bytes
from .types import ResolvedDependencies, SourceArtifact, SourceBundle

PREFIX = "pdf-domain/"
CONTRACT = PREFIX + "contract.json"


def _pdf_owner(owner: str) -> bool:
    return owner.startswith(("semantic.pdf_", "ingest.pdf")) or owner == "orchestrate.pdf_streaming"


@cache
def pdf_domain_sources() -> tuple[SourceArtifact, ...]:
    """Acquire the real owning actions and exact PDF contracts at an entry point."""
    from .contracts import compile_execution_model, trusted_execution_inputs

    inputs = trusted_execution_inputs()
    model = compile_execution_model(inputs)
    bindings = {
        binding.id: binding for binding in model.implementations if _pdf_owner(binding.owner)
    }
    actions = {
        operation.id: {
            "contract": asdict(model.require_operation(operation.id)),
            "implementation": asdict(bindings[operation.implementation]),
        }
        for operation in model.operations if operation.implementation in bindings
    }
    # Native PDF has its own standalone nominal envelope and retained staging policy.
    schema = next(source for source in inputs.schema.sources if source.name == "pdf_products")
    # Semantic domain contracts stay separate from physical Python/worker custody.
    # The prepared port's acquired implementation slice owns executable source files.
    contract_inputs = {"pdf/staging-model.yaml", "pdf/docling-validation.schema.json"}
    implementations = {
        source.name: source for source in inputs.implementations if source.name in contract_inputs
    }
    if set(implementations) != contract_inputs:
        raise ValueError("PDF domain contract inputs are incomplete")
    sources = (
        SourceArtifact(PREFIX + "schema/pdf_products", schema.content),
        SourceArtifact(PREFIX + "schema/core", (
            Path(__file__).resolve().parents[1] / "model/semantic/core.yaml"
        ).read_bytes()),
        SourceArtifact(PREFIX + "schema/pdf_domain_schema", canonical_bytes({
            "id": "urn:corpus:pdf-domain-schema", "name": "pdf_domain_schema",
            "imports": ["pdf_products", "core"],
        })),
        *(SourceArtifact(PREFIX + "implementation/" + name, source.content)
          for name, source in sorted(implementations.items())),
    )
    contract = SourceArtifact(CONTRACT, canonical_bytes({
        "version": "pdf-domain-contract-v1",
        "schema": {
            "root": "pdf_domain_schema", "sources": ["pdf_products", "core", "pdf_domain_schema"]
        },
        "actions": actions,
        "inputs": [{"name": source.name, "sha256": source.digest} for source in sources],
    }))
    return (contract, *sources)


def pdf_domain_dependencies(dependencies: ResolvedDependencies) -> ResolvedDependencies:
    if any(source.name.startswith("execution/") for source in dependencies.artifacts):
        raise ValueError("PDF domain facet cannot be attached to a legacy execution release")
    if any(source.name.startswith(PREFIX) for source in dependencies.artifacts):
        raise ValueError("PDF domain inputs use an already supplied reserved namespace")
    return ResolvedDependencies(
        (*dependencies.artifacts, *pdf_domain_sources()), dependencies.vocabularies,
        dependencies.ontology_sources,
    )


@dataclass(frozen=True)
class PdfDomainContract:
    content: bytes
    sources: tuple[SourceArtifact, ...]

    def __post_init__(self) -> None:
        contract = json.loads(self.content)
        if set(contract) != {"version", "schema", "actions", "inputs"} or (
            contract["version"] != "pdf-domain-contract-v1"
        ):
            raise ValueError("unsupported PDF domain contract")
        actual = [{"name": source.name, "sha256": source.digest} for source in self.sources]
        if actual != contract["inputs"] or (
            len({source.name for source in self.sources}) != len(actual)
        ):
            raise ValueError("PDF domain source custody differs")
        for name, action in contract["actions"].items():
            if action["contract"]["id"] != name or not _pdf_owner(
                action["implementation"]["owner"]
            ):
                raise ValueError("PDF action has a foreign or relabeled owner")

    def require_operation(self, name: str) -> dict[str, Any]:
        actions = json.loads(self.content)["actions"]
        if name not in actions:
            raise ValueError("required action is absent from archived PDF contract: " + name)
        return actions[name]

    def source(self, name: str) -> SourceArtifact:
        return next(source for source in self.sources if source.name == PREFIX + name)

    @property
    def schema(self) -> SourceBundle:
        contract = json.loads(self.content)
        return SourceBundle(contract["schema"]["root"], tuple(
            SourceArtifact(name, self.source("schema/" + name).content)
            for name in contract["schema"]["sources"]
        ))


def read_pdf_domain(connection, release_id: str) -> PdfDomainContract:
    from sqlalchemy import select

    from .metadata import table

    inputs = table("sem.input")
    rows = tuple(connection.execute(select(inputs.c.input_name, inputs.c.content).where(
        inputs.c.release_id == release_id, inputs.c.input_kind == "dependency",
        inputs.c.input_name.startswith(PREFIX),
    )))
    retained = {row.input_name: bytes(row.content) for row in rows}
    content = retained.pop(CONTRACT, None)
    if content is None:
        raise ValueError("producer has no captured PDF domain contract")
    names = [source["name"] for source in json.loads(content)["inputs"]]
    if set(names) != set(retained):
        raise ValueError("PDF domain archived source inventory differs")
    return PdfDomainContract(content, tuple(SourceArtifact(name, retained[name]) for name in names))


def pdf_domain_artifacts(dependencies: ResolvedDependencies):
    """Materialize the actual domain facet and its shared fixed-call projection."""
    from .types import PreparedArtifact

    content = next((s.content for s in dependencies.artifacts if s.name == CONTRACT), None)
    if content is None:
        return ()
    if any(source.name.startswith("execution/") for source in dependencies.artifacts):
        raise ValueError("PDF domain facet and legacy execution inputs are distinct contracts")
    names = [row["name"] for row in json.loads(content)["inputs"]]
    retained = {s.name: s for s in dependencies.artifacts if s.name.startswith(PREFIX)}
    retained.pop(CONTRACT)
    if set(retained) != set(names):
        raise ValueError("PDF domain preparation source inventory differs")
    domain = PdfDomainContract(content, tuple(retained[name] for name in names))
    actions = json.loads(domain.content)["actions"]
    calls = [
        [name, call]
        for name, action in sorted(actions.items())
        for call in action["contract"]["calls"]
    ]
    return (
        PreparedArtifact(CONTRACT, content),
        PreparedArtifact("operation_call_correspondences.json", canonical_bytes(calls)),
    )


def require_pdf_database_action(connection, release_id: str, action: str) -> None:
    """Ask the PDF owner to enforce its archived action/capability correspondence."""
    from sqlalchemy import Text, bindparam, func, select

    connection.execute(select(func.ops.require_pdf_operation(
        bindparam("_pdf_release", release_id, type_=Text()),
        bindparam("_pdf_action", action, type_=Text()),
    ))).scalar_one()
