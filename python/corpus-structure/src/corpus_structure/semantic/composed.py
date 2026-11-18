"""Explicit immutable current DDO inputs; pure preparation never discovers installed sources."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

from .identity import canonical_bytes
from .types import ResolvedDependencies, SourceArtifact, SourceBundle

if TYPE_CHECKING:
    from corpus_structure.model.compiled import CompiledModel

_PREFIX = "execution/"


# Current DDO products retain one exact source/declaration input namespace.
_DATA_PREFIX = "data-operations/"
_DATA_MANIFEST = _DATA_PREFIX + "manifest.json"


def data_operation_dependencies(
    dependencies: ResolvedDependencies,
    declarations: tuple[SourceArtifact, ...] = (),
    python_sources=None,
    *,
    declaration_model: CompiledModel | None = None,
) -> ResolvedDependencies:
    """Package operation inputs with the acquired declaration grammar."""
    from corpus_structure.schema.operation_declarations import (
        captured_declaration_model,
        declaration_sources,
    )

    from .data_operation_model import MODEL_VERSION

    if any(item.name.startswith(_PREFIX) for item in dependencies.artifacts):
        raise ValueError(
            "target data-operation preparation cannot combine legacy execution admission inputs"
        )
    if any(item.name.startswith(_DATA_PREFIX) for item in dependencies.artifacts):
        raise ValueError("data-operation inputs are already supplied or use a reserved name")
    if captured_declaration_model(dependencies.artifacts) is not None:
        raise ValueError("operation declaration sources are already supplied")
    names = [source.name for source in declarations]
    if len(names) != len(set(names)):
        raise ValueError("duplicate data-operation declaration source")
    sources = python_sources.sources if python_sources is not None else ()
    module_names = [source.module for source in sources]
    if len(module_names) != len(set(module_names)):
        raise ValueError("duplicate data-operation Python module")
    contracts = python_sources.boundary_contracts if python_sources is not None else ()
    contract_names = [source.name for source in contracts]
    if len(contract_names) != len(set(contract_names)):
        raise ValueError("duplicate Python boundary contract")
    manifest = {
        "version": MODEL_VERSION,
        "declarations": names,
        "python": None
        if python_sources is None
        else {
            "interpreter": python_sources.interpreter,
            "interpretation": python_sources.interpretation,
            "stub_policy": python_sources.stub_policy,
            "boundary_contracts": contract_names,
            **(
                {"generated_interfaces": list(python_sources.generated_interfaces)}
                if python_sources.generated_interfaces
                else {}
            ),
            "sources": [
                {"module": s.module, "filename": s.filename, "stub": s.stub is not None}
                for s in sources
            ],
        },
    }
    artifacts = [SourceArtifact(_DATA_MANIFEST, canonical_bytes(manifest))]
    artifacts += [
        SourceArtifact(_DATA_PREFIX + "declarations/" + s.name, s.content) for s in declarations
    ]
    for index, source in enumerate(sources):
        artifacts.append(SourceArtifact(_DATA_PREFIX + f"python/{index}.py", source.content))
        if source.stub is not None:
            artifacts.append(SourceArtifact(_DATA_PREFIX + f"python/{index}.pyi", source.stub))
    artifacts += [
        SourceArtifact(_DATA_PREFIX + "contracts/" + s.name, s.content) for s in contracts
    ]
    return ResolvedDependencies(
        (*dependencies.artifacts, *artifacts, *declaration_sources(declaration_model)),
        dependencies.vocabularies,
        dependencies.ontology_sources,
    )


def read_data_operation_inputs(dependencies: ResolvedDependencies):
    """Decode the closed captured manifest without imports or source discovery."""
    from .data_operation_model import MODEL_VERSION
    from .python_operation_sources import PythonSource, PythonSourceCollection

    artifacts = [
        source for source in dependencies.artifacts if source.name.startswith(_DATA_PREFIX)
    ]
    if not artifacts:
        return None
    supplied = {source.name: source for source in artifacts}
    if len(supplied) != len(artifacts) or _DATA_MANIFEST not in supplied:
        raise ValueError("data-operation inputs require one closed manifest")
    manifest = json.loads(supplied[_DATA_MANIFEST].content)
    if (
        not isinstance(manifest, dict)
        or set(manifest) != {"version", "declarations", "python"}
        or manifest["version"] != MODEL_VERSION
    ):
        raise ValueError("invalid data-operation input manifest")
    names = manifest["declarations"]
    if (
        not isinstance(names, list)
        or any(not isinstance(name, str) or not name for name in names)
        or len(names) != len(set(names))
    ):
        raise ValueError("invalid data-operation declaration names")
    expected = {_DATA_MANIFEST, *(_DATA_PREFIX + "declarations/" + name for name in names)}
    declarations = tuple(
        SourceArtifact(name, supplied[_DATA_PREFIX + "declarations/" + name].content)
        for name in names
    )
    python = manifest["python"]
    inputs = None
    if python is not None:
        if not isinstance(python, dict) or set(python) - {"generated_interfaces"} != {
            "interpreter",
            "interpretation",
            "stub_policy",
            "boundary_contracts",
            "sources",
        }:
            raise ValueError("invalid Python operation input context")
        if any(
            not isinstance(python[key], str) or not python[key]
            for key in ("interpreter", "interpretation", "stub_policy")
        ):
            raise ValueError("invalid Python operation interpretation context")
        generated_interfaces = python.get("generated_interfaces", [])
        if (
            not isinstance(generated_interfaces, list)
            or any(not isinstance(name, str) for name in generated_interfaces)
            or len(generated_interfaces) != len(set(generated_interfaces))
            or set(generated_interfaces) - {"dataclasses", "unpack-typeddict"}
        ):
            raise ValueError("invalid Python generated interface profile")
        contracts = python["boundary_contracts"]
        if (
            not isinstance(contracts, list)
            or any(not isinstance(name, str) or not name for name in contracts)
            or len(set(contracts)) != len(contracts)
        ):
            raise ValueError("invalid Python boundary contract names")
        expected.update(_DATA_PREFIX + "contracts/" + name for name in contracts)
        sources = []
        if not isinstance(python["sources"], list):
            raise ValueError("invalid Python source manifest")
        for index, record in enumerate(python["sources"]):
            if (
                not isinstance(record, dict)
                or set(record) != {"module", "filename", "stub"}
                or type(record["stub"]) is not bool
                or any(
                    not isinstance(record[key], str) or not record[key]
                    for key in ("module", "filename")
                )
            ):
                raise ValueError("invalid Python source manifest entry")
            name = _DATA_PREFIX + f"python/{index}.py"
            expected.add(name)
            stub = None
            if record["stub"]:
                expected.add(name + "i")
                stub = supplied[name + "i"].content
            sources.append(
                PythonSource(record["module"], supplied[name].content, record["filename"], stub)
            )
        inputs = PythonSourceCollection(
            tuple(sources),
            python["interpreter"],
            python["interpretation"],
            python["stub_policy"],
            tuple(
                SourceArtifact(name, supplied[_DATA_PREFIX + "contracts/" + name].content)
                for name in contracts
            ),
            tuple(generated_interfaces),
        )
    if set(supplied) != expected:
        raise ValueError("data-operation input set differs from manifest")
    return declarations, inputs


def data_operations_from_dependencies(
    bundle: SourceBundle, dependencies: ResolvedDependencies, definitions, vocabularies=()
):
    """Compile one closed supplied manifest, or return None when the feature is absent."""
    from .data_operation_static_preparation import prepare_data_operation_model

    captured = read_data_operation_inputs(dependencies)
    if captured is None:
        return None
    from corpus_structure.schema.operation_declarations import captured_declaration_model

    if captured_declaration_model(dependencies.artifacts) is None:
        raise ValueError("release preparation requires captured operation declaration sources")
    declarations, inputs = captured
    return prepare_data_operation_model(
        bundle,
        declarations,
        inputs,
        definitions=definitions,
        vocabularies=tuple(vocabularies),
        captured_contracts=dependencies.artifacts,
    )
