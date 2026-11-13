"""Explicit immutable execution inputs for the composed semantic profile.

Acquisition is an entry-point operation. Pure preparation resolves only supplied bytes;
trusted execution classes never enter the domain extraction/query class namespace.
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .contracts import ExecutionModelInputs, ExecutionModelProducts

from .identity import canonical_bytes
from .types import ResolvedDependencies, SourceArtifact, SourceBundle

_PREFIX = "execution/"
_MANIFEST = _PREFIX + "manifest.json"


def composed_dependencies(
    dependencies: ResolvedDependencies, execution: ExecutionModelInputs | None = None
) -> ResolvedDependencies:
    """Acquire the trusted model explicitly, or package an explicitly supplied candidate."""
    from .contracts import trusted_execution_inputs

    inputs = trusted_execution_inputs() if execution is None else execution
    if any(item.name.startswith(_PREFIX) for item in dependencies.artifacts):
        raise ValueError("execution inputs are already supplied or use a reserved name")
    schema_names = [item.name for item in inputs.schema.sources]
    if len(schema_names) != len(set(schema_names)):
        raise ValueError("duplicate execution schema input")
    artifacts = (
        SourceArtifact(
            _MANIFEST,
            canonical_bytes(
                {
                    "root": inputs.schema.root,
                    "schemas": schema_names,
                    "catalog": inputs.catalog.name,
                    "implementations": [item.name for item in inputs.implementations],
                }
            ),
        ),
        SourceArtifact(_PREFIX + "catalog.yaml", inputs.catalog.content),
        *(
            SourceArtifact(_PREFIX + "implementation/" + item.name, item.content)
            for item in inputs.implementations
        ),
        *(
            SourceArtifact(_PREFIX + "schema/" + item.name, item.content)
            for item in inputs.schema.sources
        ),
    )
    return ResolvedDependencies(
        (*dependencies.artifacts, *artifacts),
        dependencies.vocabularies,
        dependencies.ontology_sources,
    )


def execution_model_from_dependencies(dependencies: ResolvedDependencies) -> ExecutionModelProducts:
    """Resolve and compile supplied contract bytes, with no installed-model fallback."""
    from .contracts import ExecutionModelInputs, compile_execution_model

    sources = {item.name: item for item in dependencies.artifacts if item.name.startswith(_PREFIX)}
    if len(sources) != sum(item.name.startswith(_PREFIX) for item in dependencies.artifacts):
        raise ValueError("duplicate execution input")
    if _MANIFEST not in sources:
        raise ValueError("semantic-2 requires explicit execution inputs")
    manifest = json.loads(sources[_MANIFEST].content)
    if (
        set(manifest) != {"root", "schemas", "catalog", "implementations"}
        or not isinstance(manifest["root"], str)
        or not isinstance(manifest["schemas"], list)
        or not isinstance(manifest["catalog"], str)
        or not manifest["catalog"]
    ):
        raise ValueError("invalid execution input manifest")
    names = manifest["schemas"]
    if any(not isinstance(name, str) or not name for name in names) or len(names) != len(
        set(names)
    ):
        raise ValueError("invalid execution schema names")
    implementation_names = manifest["implementations"]
    if (
        not isinstance(implementation_names, list)
        or any(not isinstance(name, str) for name in implementation_names)
        or len(set(implementation_names)) != len(implementation_names)
    ):
        raise ValueError("invalid execution implementation names")
    expected = {
        *(_PREFIX + "implementation/" + name for name in implementation_names),
        _MANIFEST,
        _PREFIX + "catalog.yaml",
        *(_PREFIX + "schema/" + name for name in names),
    }
    if set(sources) != expected:
        raise ValueError("execution input set differs from manifest")
    bundle = SourceBundle(
        manifest["root"],
        tuple(SourceArtifact(name, sources[_PREFIX + "schema/" + name].content) for name in names),
    )
    inputs = ExecutionModelInputs(
        bundle,
        SourceArtifact(manifest["catalog"], sources[_PREFIX + "catalog.yaml"].content),
        tuple(
            SourceArtifact(name, sources[_PREFIX + "implementation/" + name].content)
            for name in implementation_names
        ),
    )
    return compile_execution_model(inputs)


# This opt-in namespace archives the new effective products without routing
# existing operations to the new runtime/storage protocol.
_DATA_PREFIX = "data-operations/"
_DATA_MANIFEST = _DATA_PREFIX + "manifest.json"


def data_operation_dependencies(
    dependencies: ResolvedDependencies,
    declarations: tuple[SourceArtifact, ...] = (),
    python_sources=None,
) -> ResolvedDependencies:
    """Package explicitly acquired operation inputs; never discover installed sources."""
    from .data_operation_model import MODEL_VERSION

    if any(item.name.startswith(_PREFIX) for item in dependencies.artifacts):
        raise ValueError(
            "target data-operation preparation cannot combine legacy execution admission inputs"
        )
    if any(item.name.startswith(_DATA_PREFIX) for item in dependencies.artifacts):
        raise ValueError("data-operation inputs are already supplied or use a reserved name")
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
        (*dependencies.artifacts, *artifacts),
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
    from .data_operation_compilation import compile_data_operations

    captured = read_data_operation_inputs(dependencies)
    if captured is None:
        return None
    declarations, inputs = captured
    return compile_data_operations(
        bundle, declarations, inputs, definitions=definitions, vocabularies=tuple(vocabularies)
    )
