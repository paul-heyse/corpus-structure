"""Data-only kernel recipes and the one native DDO admission sequence.

TS17 deliberately retains a fresh deployed-head clone per case. Preparation may be
reused within a worker; committed database state is never shared between cases here.
"""

from __future__ import annotations

import copy
import json
from collections.abc import Iterator, Mapping
from dataclasses import dataclass
from functools import cache
from pathlib import Path
from tempfile import TemporaryDirectory
from types import MappingProxyType
from typing import Any

import yaml
from scenario_recipes import register_scenario_builder
from sqlalchemy import Connection, Engine, insert, select

from corpus_structure.semantic.contracts import implementation_overridden
from corpus_structure.semantic.data_operation_admission import (
    admit_data_operation_release,
    bound_data_operation_model,
)
from corpus_structure.semantic.data_operation_consumers import consumer_selection_declarations
from corpus_structure.semantic.data_operation_model import EffectiveDataOperationModel
from corpus_structure.semantic.data_operation_preparation import prepare_data_operation_inputs
from corpus_structure.semantic.data_operation_runtime import prepare_data_operation_runtime
from corpus_structure.semantic.identity import canonical_bytes
from corpus_structure.semantic.metadata import table
from corpus_structure.semantic.python_operation_sources import PythonSource
from corpus_structure.semantic.releases import persist_release
from corpus_structure.semantic.runtime_binding_store import persist_runtime_binding
from corpus_structure.semantic.runtime_bindings import RuntimeBinding
from corpus_structure.semantic.types import (
    PreparationProfile,
    PreparedRelease,
    ResolvedDependencies,
    SourceBundle,
)
from semantic.data_operation_declaration_support import (
    _consumer_declaration,
    _evaluator_declaration,
    _sample_declaration,
    _set_declaration,
    _value_consumer_declaration,
    source_declaration,
)


@dataclass(frozen=True)
class KernelRecipe:
    name: str
    schema_text: str
    declaration_content: bytes | None
    manifest_text: str
    execution_profile: str = "execution:test"
    project_id: str | None = "ddo-test"
    declaration_path: str = "operations.yaml"
    additional_files: tuple[tuple[str, bytes], ...] = ()
    python_sources: tuple[tuple[str, str, bytes], ...] = ()
    source_stage: str | None = None

    @property
    def model_version(self):
        return (
            None
            if self.declaration_content is None
            else json.loads(self.declaration_content)["version"]
        )

    @property
    def kinds(self):
        return (
            ()
            if self.declaration_content is None
            else tuple(json.loads(self.declaration_content).get("kinds", ()))
        )


@dataclass(frozen=True)
class KernelPreparation:
    bundle: SourceBundle
    dependencies: ResolvedDependencies
    profile: PreparationProfile
    prepared: PreparedRelease
    model: EffectiveDataOperationModel
    runtime: RuntimeBinding
    directory: Path
    directory_owner: TemporaryDirectory[str] | None


def _prepare_kernel(recipe: KernelRecipe, directory: Path | None = None) -> KernelPreparation:
    owner = TemporaryDirectory(prefix="ddo-" + recipe.name + "-") if directory is None else None
    directory = Path(owner.name) if owner is not None else directory
    assert directory is not None
    (directory / "schema.yaml").write_text(recipe.schema_text)
    if recipe.declaration_content is not None:
        (directory / recipe.declaration_path).write_bytes(recipe.declaration_content)
    for name, content in recipe.additional_files:
        (directory / name).write_bytes(content)
    for _module, name, content in recipe.python_sources:
        (directory / name).write_bytes(content)
    (directory / "target.yaml").write_text(recipe.manifest_text)
    bundle, dependencies, profile, prepared = prepare_data_operation_inputs(
        directory, "target.yaml"
    )
    model = bound_data_operation_model(prepared)
    runtime = prepare_data_operation_runtime(
        prepared, dependencies.artifacts, execution_profile=recipe.execution_profile, observed={}
    )
    return KernelPreparation(
        bundle, dependencies, profile, prepared, model, runtime, directory, owner
    )


_prepared_kernel = cache(_prepare_kernel)


def prepare_kernel(recipe: KernelRecipe, *, directory: Path | None = None) -> KernelPreparation:
    if directory is not None:
        return _prepare_kernel(recipe, directory)
    # An override bypasses both reads and writes, preserving the ordinary warm entry.
    return _prepare_kernel(recipe) if implementation_overridden() else _prepared_kernel(recipe)


@dataclass(frozen=True)
class Kernel(Mapping[str, Any]):
    engine: Engine
    preparation: KernelPreparation
    identities: Mapping[tuple[str, str], str]
    recipe: KernelRecipe
    clone: Any = None

    def purpose(self, name):
        if self.clone is None:
            raise ValueError("purpose acquisition requires a kernel clone")
        return self.clone.purpose(name)

    @property
    def prepared(self) -> PreparedRelease:
        return self.preparation.prepared

    @property
    def model(self) -> EffectiveDataOperationModel:
        return self.preparation.model

    @property
    def runtime(self) -> str:
        return self.preparation.runtime.runtime_id

    @property
    def runtime_inputs(self):
        return self.preparation.dependencies.artifacts

    @property
    def kind(self):
        operation = self.model.operation("urn:ddo-test:source")
        role = next(role for role in operation.roles if role.direction == "output")
        return self.identities[role.kind, "kind"]

    def __getitem__(self, name):
        if name not in tuple(self):
            raise KeyError(name)
        return getattr(self, name)

    def __iter__(self) -> Iterator[str]:
        return iter(
            (
                "engine",
                "prepared",
                "model",
                "runtime",
                "runtime_inputs",
                "identities",
                "recipe",
                "kind",
            )
        )

    def __len__(self):
        return 8


def admit_kernel(
    connection: Connection,
    recipe: KernelRecipe,
    *,
    engine: Engine | None = None,
    preparation: KernelPreparation | None = None,
) -> Kernel:
    preparation = prepare_kernel(recipe) if preparation is None else preparation
    persist_release(
        connection,
        preparation.bundle,
        preparation.dependencies,
        preparation.profile,
        preparation.prepared,
    )
    admit_data_operation_release(connection, preparation.prepared)
    persist_runtime_binding(connection, preparation.prepared, preparation.runtime)
    if recipe.project_id is not None:
        connection.execute(insert(table("data.project")).values(project_id=recipe.project_id))
    identities = MappingProxyType(
        {(item.owner, item.domain): item.key for item in preparation.model.identities}
    )
    return Kernel(
        engine if engine is not None else connection.engine, preparation, identities, recipe
    )


@dataclass(frozen=True)
class KernelSeedStage:
    preparation: KernelPreparation
    identities: Mapping[tuple[str, str], str]
    recipe: KernelRecipe

    @property
    def seed_files(self) -> tuple[Path, ...]:
        return tuple(
            sorted(path for path in self.preparation.directory.rglob("*") if path.is_file())
        )

    def validate_clone(self, admin: Engine) -> None:
        from corpus_structure.semantic.runtime_binding_store import runtime_binding_for_release

        definitions = table("sem.data_operation_definition")
        with admin.connect() as connection:
            binding = runtime_binding_for_release(
                connection, self.preparation.prepared, self.preparation.runtime.runtime_id
            )
            if binding != self.preparation.runtime:
                raise ValueError("kernel seed runtime custody differs")
            actual = set(
                connection.scalars(
                    select(definitions.c.operation_id).where(
                        definitions.c.release_id == self.preparation.prepared.release_id
                    )
                )
            )
            if actual != {operation.semantic_id for operation in self.preparation.model.operations}:
                raise ValueError("kernel seed admitted operations differ")


def build_kernel(recipe, admin, writer, directory, *, purpose_engine=None):
    preparation = prepare_kernel(recipe, directory=directory)
    with admin.begin() as connection:
        kernel = admit_kernel(connection, recipe, engine=admin, preparation=preparation)
    return KernelSeedStage(preparation, kernel.identities, recipe)


register_scenario_builder(KernelRecipe, build_kernel)


def kernel_clone(request, scenario_seeds):
    recipe = getattr(request, "param", None)
    if not isinstance(recipe, KernelRecipe):
        raise TypeError("ddo_kernel requires a KernelRecipe")
    with scenario_seeds.commit_clone(recipe) as clone:
        stage = clone.stage
        if not isinstance(stage, KernelSeedStage):
            raise TypeError("kernel recipe produced a different stage")
        yield Kernel(clone.admin, stage.preparation, stage.identities, recipe, clone)


MANIFEST = """version: data-operation-inputs-v1
root: target
schemas: [{name: target, path: schema.yaml}]
declarations: [{name: test-operations, path: operations.yaml}]
"""

STORAGE = KernelRecipe(
    "storage",
    """id: urn:ddo-test
name: target
prefixes: {t: 'urn:ddo-test:'}
default_prefix: t
types:
  integer: {base: int, uri: 'http://www.w3.org/2001/XMLSchema#integer'}
  string: {base: str, uri: 'http://www.w3.org/2001/XMLSchema#string'}
classes:
  Thing: {}
  Sample:
    attributes:
      value: {range: integer, required: true}
""",
    canonical_bytes(
        {
            "version": "data-operation-model-v1",
            "operations": [
                source_declaration(),
                _sample_declaration(),
                _consumer_declaration(),
                _value_consumer_declaration(),
                _set_declaration(),
                _evaluator_declaration(),
            ],
            "kinds": [
                {
                    "id": "urn:ddo-test:evaluator-integer",
                    "primitive": "integer",
                    "universe": "evaluator",
                }
            ],
        }
    ),
    MANIFEST,
)


def _population_recipe():
    producer = source_declaration()
    producer.update(id="urn:discover", profile="discovery")
    producer["roles"][0].update(kind="Population", maximum=1, collection="scalar")
    consumer = source_declaration()
    consumer.update(id="urn:consumer", dependencies=["urn:discover"])
    consumer["roles"].insert(
        0,
        {
            "name": "items",
            "kind": "Sample",
            "direction": "input",
            "minimum": 1,
            "maximum": None,
            "collection": "set",
            "presence": "required",
            "subject_field": "document_subject",
            "support": {
                "provenance": "exact",
                "source": "same-original",
                "coverage": "selected-scope",
                "identity_requirements": ["episode"],
            },
        },
    )
    consumer["binding"] = {
        "operator": "forall",
        "roles": ["items"],
        "population": "selected-items",
        "children": [
            {
                "operator": "range",
                "operands": [
                    {
                        "kind": "field",
                        "value_type": "integer",
                        "field": {"role": "items", "projection": "Sample", "field": "value"},
                    },
                    {"kind": "literal", "value_type": "integer", "value": 10},
                    {"kind": "literal", "value_type": "integer", "value": 20},
                ],
            }
        ],
    }
    child = source_declaration()
    child["id"] = "urn:child"
    return KernelRecipe(
        "population",
        """id: urn:ddo-selection
name: target
prefixes: {t: 'urn:ddo-selection:'}
default_prefix: t
types:
  integer: {base: int, uri: 'http://www.w3.org/2001/XMLSchema#integer'}
  string: {base: str, uri: 'http://www.w3.org/2001/XMLSchema#string'}
  boolean: {base: bool, uri: 'http://www.w3.org/2001/XMLSchema#boolean'}
classes:
  Scope:
    attributes:
      page: {range: integer, required: true}
  Context:
    attributes:
      subject: {range: string, required: true}
      original_source: {range: string, required: true}
      analyzed_scope: {range: Scope, required: true, inlined: true}
  Sample:
    attributes:
      value: {range: integer, required: true}
      document_subject: {range: string, required: true}
  Packet:
    attributes:
      member_id: {range: string, required: true}
      kind_contract: {range: string, required: true}
      context: {range: Context, required: true, inlined: true}
      body: {range: Sample, required: true, inlined: true}
  Population:
    attributes:
      complete: {range: boolean, required: true}
      members: {range: Packet, minimum_cardinality: 0, multivalued: true, inlined_as_list: true}
""",
        canonical_bytes(
            {"version": "data-operation-model-v1", "operations": [producer, consumer, child]}
        ),
        MANIFEST,
    )


POPULATION = _population_recipe()

PREFIX = "https://corpus-structure.dev/semantic/data-operation-consumers/"
KINDS = {
    "views": "DdoSourceViewBinding",
    "passages": "DdoPassageBinding",
    "readings": "DdoReadingBinding",
    "occurrences": "DdoOccurrenceBinding",
}
CASES = {
    "document": ("text.native_evidence/selection", "document", ("views",)),
    "projection": ("extract.m1_candidates/selection", "document", ("views",)),
    "structural": ("structure.compare/selection", "input", ("passages", "readings")),
    "occurrences": ("retrieve.contextual/selection", "view", ("views", "occurrences")),
}


def consumer_recipe(case):
    root = Path(__file__).resolve().parents[2] / "src/corpus_structure"
    schema = yaml.safe_load((root / "model/semantic/data-operation-consumers.yaml").read_text())
    schema["classes"]["ConsumerScope"] = {
        "attributes": {
            "page": {"range": "DdoBindingInteger"},
        }
    }
    schema["classes"]["ConsumerContext"] = {
        "attributes": {
            "subject": {"required": True},
            "original_source": {"required": True},
            "analyzed_scope": {"range": "ConsumerScope", "required": True, "inlined": True},
        }
    }
    operation_id, _, groups = CASES[case]
    declarations: list[dict[str, Any]] = []
    for group in groups:
        kind = KINDS[group]
        packet, population = "ConsumerPacket_" + group, "ConsumerPopulation_" + group
        schema["classes"][packet] = {
            "attributes": {
                "member_id": {"required": True},
                "kind_contract": {"required": True},
                "context": {"range": "ConsumerContext", "required": True, "inlined": True},
                "body": {"range": kind, "required": True, "inlined": True},
            }
        }
        schema["classes"][population] = {
            "attributes": {
                "complete": {"range": "DdoBindingBoolean", "required": True},
                "members": {
                    "range": packet,
                    "required": True,
                    "multivalued": True,
                    "inlined_as_list": True,
                },
            }
        }
        operation = source_declaration()
        operation.update(id="urn:consumer-native:" + group, profile="discovery")
        operation["roles"][0].update(kind=population, collection="scalar", maximum=1)
        declarations.append(operation)
    sources = tuple(
        PythonSource(name, (root / "methods" / (name + ".py")).read_bytes(), name + ".py")
        for name in ("native_evidence", "m1_source", "structural_products", "contextual_candidates")
    )
    actual = next(
        operation
        for artifact in consumer_selection_declarations(sources)
        for operation in json.loads(artifact.content)["operations"]
        if operation["id"] == operation_id
    )
    actual = copy.deepcopy(actual)
    # Explicit control producers close the actual consumer's input population.
    # Its roles, predicates, source policy and selections remain the colocated contract.
    actual["dependencies"] = [operation["id"] for operation in declarations]
    declarations.append(actual)
    return KernelRecipe(
        "consumer-" + case,
        yaml.safe_dump(schema, sort_keys=False),
        canonical_bytes({"version": "data-operation-model-v2", "operations": declarations}),
        MANIFEST.replace("test-operations", "actual-consumer-and-controls"),
    )


CONSUMERS = {case: consumer_recipe(case) for case in CASES}


def _execution_recipe():
    name = "ddo_execution_fixture"
    metadata = source_declaration()
    metadata["id"] = "urn:ddo-execution:answer"
    metadata["roles"][0].update(collection="scalar", maximum=1, kind="primitive:integer")
    metadata["parameters"] = {"value": {"value_type": "integer", "default": 7}}
    metadata["capabilities"]["cancellation"] = "call-boundary"
    source = (
        "def answer(*, value: int = 7) -> int:\n    return value\n"
        f"answer__data_operation__ = {metadata!r}\n"
    )
    failed_metadata = {**metadata, "id": "urn:ddo-execution:broken"}
    source += (
        "def broken(*, value: int = 7) -> int:\n    raise ValueError('calculation failed')\n"
        f"broken__data_operation__ = {failed_metadata!r}\n"
    )
    return KernelRecipe(
        "execution",
        """id: urn:exec
name: target
prefixes: {x: "urn:exec:"}
default_prefix: x
types:
  integer: {base: int, uri: "http://www.w3.org/2001/XMLSchema#integer"}
classes:
  Thing: {}
""",
        None,
        """version: data-operation-inputs-v1
root: target
schemas: [{name: target, path: schema.yaml}]
python:
  sources: [{module: ddo_execution_fixture, path: ddo_execution_fixture.py}]
  interpreter: python-3.14
  interpretation: closed-python-operations-v1
  stub_policy: source-authoritative
""",
        project_id="execution",
        python_sources=((name, name + ".py", source.encode()),),
    )


EXECUTION = _execution_recipe()

CLAIM_SOURCE_PATH = Path(__file__).parents[2] / "src/corpus_structure/semantic/identity.py"
CLAIM_SOURCE = KernelRecipe(
    "claim-source",
    """id: urn:production-claim-test
name: target
prefixes: {t: 'urn:production-claim-test:'}
default_prefix: t
classes:
  Thing: {}
""",
    canonical_bytes({"version": "data-operation-model-v1", "operations": [source_declaration()]}),
    """version: data-operation-inputs-v1
root: target
schemas: [{name: target, path: schema.yaml}]
declarations: [{name: ordinal-source, path: seed.yaml}]
python:
  sources: [{module: corpus_structure.semantic.identity, path: identity.py}]
  interpreter: python-3.14
  interpretation: closed-python-operations-v1
  stub_policy: source-authoritative
""",
    declaration_path="seed.yaml",
    python_sources=(
        ("corpus_structure.semantic.identity", "identity.py", CLAIM_SOURCE_PATH.read_bytes()),
    ),
)


def _original_recipe(kind, execution_profile):
    operation = source_declaration()
    operation.update(id="urn:original-fact-test:consume", behavior="source-value-consumer-v1")
    operation["roles"][0].update(maximum=1, collection="scalar")
    if kind == "DdoOriginalDocument":
        operation["capabilities"]["preparation"] = "pdf-native"
    operation["roles"].insert(
        0,
        {
            "name": "source",
            "kind": kind,
            "direction": "input",
            "minimum": 1,
            "maximum": 1,
            "collection": "scalar",
            "presence": "required",
            "support": {
                "provenance": "value_substitution",
                "source": "same-original",
                "coverage": "selected-scope",
                "identity_requirements": [],
                "origins": ["original-source"],
            },
        },
    )
    core = Path(__file__).parents[2] / "src/corpus_structure/model/semantic/core.yaml"
    manifest = """version: data-operation-inputs-v1
root: target
schemas: [{name: target, path: schema.yaml}, {name: core, path: core.yaml}]
declarations: [{name: operations, path: operations.yaml}]
source_bindings: true
"""
    if kind == "DdoOriginalDocument":
        manifest += "pdf_contracts: true\n"
    return KernelRecipe(
        "original-pdf" if kind == "DdoOriginalDocument" else "original-fact",
        """id: urn:original-fact-test
name: target
imports: [core]
prefixes: {t: 'urn:original-fact-test:'}
default_prefix: t
classes: {Marker: {}}
""",
        canonical_bytes({"version": "data-operation-model-v1", "operations": [operation]}),
        manifest,
        execution_profile=execution_profile,
        project_id=None,
        additional_files=(("core.yaml", core.read_bytes()),),
        source_stage="private-source",
    )


ORIGINAL_FACT = _original_recipe("DdoSelectedNativeSource", "execution:original-fact")
ORIGINAL_PDF = _original_recipe("DdoOriginalDocument", "execution:original-pdf")


def original_target(tmp_path, request):
    recipe = (
        ORIGINAL_PDF if getattr(request, "param", None) == "DdoOriginalDocument" else ORIGINAL_FACT
    )
    preparation = prepare_kernel(recipe)
    return preparation.bundle, preparation.dependencies, preparation.profile, preparation.prepared
