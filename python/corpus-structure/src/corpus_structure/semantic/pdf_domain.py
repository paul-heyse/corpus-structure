"""PDF-owned contract projection for native document data operations.

This projects existing declared producer/reader actions; it does not recreate a
legacy execution model or infer permissions from an operation-name prefix.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from hashlib import sha256
from pathlib import Path
from typing import Any

from .identity import canonical_bytes
from .types import ResolvedDependencies, SourceArtifact, SourceBundle

PREFIX = "pdf-domain/"
CONTRACT = PREFIX + "contract.json"


def _pdf_action(operation: str, owner: str, symbol: str) -> bool:
    return (
        owner.startswith(("semantic.pdf_", "ingest.pdf"))
        or owner == "orchestrate.pdf_streaming"
        # This genuine shared reader owns the existing PDF projection/context calls.
        or (
            owner == "semantic.source_views"
            and {
                "read_native_source": "read_native_source",
                "read_source_view": "load_source_view",
                "publish_source_view": "store_source_view",
            }.get(operation)
            == symbol
        )
    )


HELPER_CONTRACT = "pdf-native/helper-bindings"
ANALYSIS_RUNTIME = PREFIX + "analysis/libraries.json"


def _action_sources(*, physical_sources=None, linkml_types=None):
    """Read explicit current PDF helper declarations and their actual field owners."""
    import yaml
    from cattrs import Converter

    from corpus_structure.schema.physical import (
        PHYSICAL_ROOT,
        linkml_types_source,
        physical_source_closure,
    )

    from .native_call_contracts import OperationCallBinding
    from .native_call_sources import resolve_call_bindings

    root = Path(__file__).resolve().parents[1] / "model/semantic"
    action_source = SourceArtifact(
        PREFIX + "native/actions.yaml", root.joinpath("pdf-actions.yaml").read_bytes()
    )
    document = yaml.safe_load(action_source.content)
    if (
        not isinstance(document, dict)
        or set(document) != {"version", "actions", "diagnostics"}
        or document["version"] != "pdf-native-actions-v1"
    ):
        raise ValueError("unsupported current PDF helper declarations")
    converter = Converter(forbid_extra_keys=True)
    declared = {}
    calls = []
    for action in document["actions"]:
        if set(action) != {"id", "implementation", "outcomes", "calls"} or action["id"] in declared:
            raise ValueError("invalid or duplicate current PDF action")
        implementation = action["implementation"]
        if set(implementation) != {"owner", "symbol", "version"} or not _pdf_action(
            action["id"], implementation["owner"], implementation["symbol"]
        ):
            raise ValueError("PDF action has a foreign or relabeled owner")
        declared[action["id"]] = action
        for call in action["calls"]:
            for value in (
                *call["parameters"],
                *call["result_fields"],
                *(field for record in call.get("records", ()) for field in record["fields"]),
            ):
                value.setdefault("nullable", False)
            calls.append((action["id"], converter.structure(call, OperationCallBinding)))
    physical = (
        physical_source_closure(PHYSICAL_ROOT, lambda name: root.joinpath(name).read_bytes())
        if physical_sources is None
        else dict(physical_sources)
    )
    if physical_sources is not None and not isinstance(linkml_types, bytes):
        raise ValueError("explicit PDF physical capture requires LinkML types")
    logical = {
        name: physical[filename] if filename in physical else root.joinpath(filename).read_bytes()
        for name, filename in (
            ("pdf_products", "pdf-products.yaml"),
            ("core", "core.yaml"),
            ("pdf_records", "pdf-records.yaml"),
            ("pdf_staging", "pdf-staging.yaml"),
            ("read_projections", "read-projections.yaml"),
            ("companion_projections", "companion-projections.yaml"),
            ("selected_source", "selected-source.yaml"),
        )
    }
    logical["linkml:types"] = linkml_types_source() if linkml_types is None else linkml_types
    resolved = resolve_call_bindings(
        tuple(calls), logical_sources=logical, physical_sources=physical
    )
    actions = {
        name: {
            "contract": {
                "id": name,
                "outcomes": action["outcomes"],
                "calls": [asdict(call) for owner, call in resolved if owner == name],
            },
            "implementation": action["implementation"],
        }
        for name, action in declared.items()
    }
    sources = (
        action_source,
        *(
            SourceArtifact(PREFIX + "logical/" + name, content)
            for name, content in sorted(logical.items())
        ),
        *(
            SourceArtifact(PREFIX + "physical/" + name, content)
            for name, content in sorted(physical.items())
        ),
    )
    return actions, sources, document["diagnostics"]


def pdf_domain_sources(*, physical_sources=None, linkml_types=None) -> tuple[SourceArtifact, ...]:
    """Acquire current PDF helper assets without an execution catalog/compiler."""
    actions, action_sources, diagnostics = _action_sources(
        physical_sources=physical_sources, linkml_types=linkml_types
    )
    root = Path(__file__).resolve().parents[1] / "model/semantic"
    supplied = dict(physical_sources or {})

    def content(name):
        return supplied[name] if name in supplied else root.joinpath(name).read_bytes()

    from .determinants import analysis_runtime

    sources = (
        *action_sources,
        SourceArtifact(ANALYSIS_RUNTIME, canonical_bytes(dict(analysis_runtime()))),
        SourceArtifact(
            PREFIX + "schema/pdf_products", root.joinpath("pdf-products.yaml").read_bytes()
        ),
        SourceArtifact(PREFIX + "schema/core", root.joinpath("core.yaml").read_bytes()),
        SourceArtifact(
            PREFIX + "schema/pdf_domain_schema",
            canonical_bytes(
                {
                    "id": "urn:corpus:pdf-domain-schema",
                    "name": "pdf_domain_schema",
                    "imports": ["pdf_products", "core"],
                }
            ),
        ),
        SourceArtifact(
            PREFIX + "implementation/pdf/staging-model.yaml", content("pdf-staging.yaml")
        ),
        SourceArtifact(
            PREFIX + "implementation/pdf/docling-validation.schema.json",
            root.joinpath("docling-validation.schema.json").read_bytes(),
        ),
        SourceArtifact(
            PREFIX + "native/data-operation-protocol.yaml", content("data-operation-native.yaml")
        ),
    )
    contract = SourceArtifact(
        CONTRACT,
        canonical_bytes(
            {
                "version": "pdf-domain-contract-v2",
                "schema": {
                    "root": "pdf_domain_schema",
                    "sources": ["pdf_products", "core", "pdf_domain_schema"],
                },
                "actions": actions,
                "diagnostics": diagnostics,
                "inputs": [{"name": source.name, "sha256": source.digest} for source in sources],
            }
        ),
    )
    return (contract, *sources)


def pdf_helper_asset() -> SourceArtifact:
    source = next(source for source in pdf_domain_sources() if source.name == CONTRACT)
    return SourceArtifact(HELPER_CONTRACT, source.content)


def pdf_domain_dependencies(dependencies: ResolvedDependencies) -> ResolvedDependencies:
    if any(source.name.startswith("execution/") for source in dependencies.artifacts):
        raise ValueError("PDF domain facet cannot be attached to a legacy execution release")
    if any(source.name.startswith(PREFIX) for source in dependencies.artifacts):
        raise ValueError("PDF domain inputs use an already supplied reserved namespace")
    return ResolvedDependencies(
        (*dependencies.artifacts, *pdf_domain_sources()),
        dependencies.vocabularies,
        dependencies.ontology_sources,
    )


@dataclass(frozen=True)
class PdfDomainContract:
    content: bytes
    sources: tuple[SourceArtifact, ...]

    def __post_init__(self) -> None:
        contract = json.loads(self.content)
        if set(contract) != {"version", "schema", "actions", "inputs", "diagnostics"} or (
            contract["version"] != "pdf-domain-contract-v2"
        ):
            raise ValueError("unsupported PDF domain contract")
        actual = [{"name": source.name, "sha256": source.digest} for source in self.sources]
        if actual != contract["inputs"] or (
            len({source.name for source in self.sources}) != len(actual)
        ):
            raise ValueError("PDF domain source custody differs")
        for name, action in contract["actions"].items():
            if action["contract"]["id"] != name or not _pdf_action(
                name, action["implementation"]["owner"], action["implementation"]["symbol"]
            ):
                raise ValueError("PDF action has a foreign or relabeled owner")

    def require_operation(self, name: str) -> dict[str, Any]:
        actions = json.loads(self.content)["actions"]
        if name not in actions:
            raise ValueError("required action is absent from archived PDF contract: " + name)
        return actions[name]

    @property
    def invariants(self):
        from cattrs import Converter

        from .invariant_failures import NativeInvariant

        return Converter(forbid_extra_keys=True).structure(
            json.loads(self.content)["diagnostics"], tuple[NativeInvariant, ...]
        )

    def source(self, name: str) -> SourceArtifact:
        return next(source for source in self.sources if source.name == PREFIX + name)

    @property
    def schema(self) -> SourceBundle:
        contract = json.loads(self.content)
        return SourceBundle(
            contract["schema"]["root"],
            tuple(
                SourceArtifact(name, self.source("schema/" + name).content)
                for name in contract["schema"]["sources"]
            ),
        )


def read_pdf_domain(connection, release_id: str) -> PdfDomainContract:
    from sqlalchemy import select

    from .metadata import table

    inputs = table("sem.input")
    rows = tuple(
        connection.execute(
            select(inputs.c.input_name, inputs.c.content).where(
                inputs.c.release_id == release_id,
                inputs.c.input_kind == "dependency",
                inputs.c.input_name.startswith(PREFIX),
            )
        )
    )
    retained = {row.input_name: bytes(row.content) for row in rows}
    content = retained.pop(CONTRACT, None)
    if content is None:
        raise ValueError("producer has no captured PDF domain contract")
    names = [source["name"] for source in json.loads(content)["inputs"]]
    if set(names) != set(retained):
        raise ValueError("PDF domain archived source inventory differs")
    return PdfDomainContract(content, tuple(SourceArtifact(name, retained[name]) for name in names))


def pdf_domain_artifacts(dependencies: ResolvedDependencies, *, model=None):
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
    require_pdf_model_asset(model, domain)
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


def require_pdf_model_asset(model, domain: PdfDomainContract) -> None:
    """Helper bindings are assets of an actual checked PDF operation."""
    digest = sha256(domain.content).hexdigest()
    if model is None or not any(
        operation.capabilities.preparation == "pdf-native"
        and any(
            asset.reference == CONTRACT
            and asset.contract == HELPER_CONTRACT
            and asset.role == "native-pdf-helper-bindings"
            and asset.content_digest == digest
            for asset in operation.assets
        )
        for operation in model.operations
    ):
        raise ValueError("PDF helper contract is not bound by a checked native PDF operation")


def require_pdf_prepared_action(prepared, operation: str):
    """Read the helper asset authenticated by the current effective DDO model."""
    from .data_operation_admission import bound_data_operation_model

    model = bound_data_operation_model(prepared)
    retained = [artifact for artifact in prepared.artifacts if artifact.kind == CONTRACT]
    if len(retained) != 1:
        raise ValueError("release lacks one current PDF helper contract")
    artifact = retained[0]
    if not any(
        op.capabilities.preparation == "pdf-native"
        and any(
            asset.reference == CONTRACT
            and asset.contract == HELPER_CONTRACT
            and asset.role == "native-pdf-helper-bindings"
            and asset.content_digest == artifact.digest
            for asset in op.assets
        )
        for op in model.operations
    ):
        raise ValueError("PDF helper contract is not bound by a checked native PDF operation")
    contract = json.loads(artifact.content)
    if (
        set(contract) != {"version", "schema", "actions", "inputs", "diagnostics"}
        or contract["version"] != "pdf-domain-contract-v2"
    ):
        raise ValueError("unsupported current PDF helper contract")
    action = contract["actions"].get(operation)
    if (
        action is None
        or action["contract"]["id"] != operation
        or not _pdf_action(
            operation, action["implementation"]["owner"], action["implementation"]["symbol"]
        )
    ):
        raise ValueError("required action is absent from current PDF helper contract: " + operation)
    return action


def require_pdf_call_context(prepared, operation: str, variant: str, contract_digest: str) -> None:
    from .refusals import SemanticRefusal

    action = require_pdf_prepared_action(prepared, operation)
    calls = [call for call in action["contract"]["calls"] if call["id"] == variant]
    if len(calls) != 1 or sha256(canonical_bytes(calls)).hexdigest() != contract_digest:
        raise SemanticRefusal(f"{operation}/{variant}: incompatible PDF helper call correspondence")


def pdf_call_bindings(domain: PdfDomainContract | None = None):
    content = pdf_domain_sources()[0].content if domain is None else domain.content
    from cattrs import Converter

    from .native_call_contracts import OperationCallBinding

    converter = Converter(forbid_extra_keys=True)
    return tuple(
        (name, converter.structure(call, OperationCallBinding))
        for name, action in json.loads(content)["actions"].items()
        for call in action["contract"]["calls"]
    )


def require_pdf_database_action(connection, release_id: str, action: str) -> None:
    """Ask the PDF owner to enforce its archived action/capability correspondence."""
    from sqlalchemy import Text, bindparam, func, select

    connection.execute(
        select(
            func.ops.require_pdf_operation(
                bindparam("_pdf_release", release_id, type_=Text()),
                bindparam("_pdf_action", action, type_=Text()),
            )
        )
    ).scalar_one()
