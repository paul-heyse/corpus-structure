"""Independent DDO-01 effective facts, closure and identity projection controls."""

from __future__ import annotations

import json
from dataclasses import replace
from pathlib import Path
from typing import Any

import pytest

from corpus_structure.semantic.composed import data_operation_dependencies
from corpus_structure.semantic.data_operation_compilation import (
    compile_data_operations,
    project_operation_binding,
)
from corpus_structure.semantic.data_operation_identity import semantic_value
from corpus_structure.semantic.data_operation_model import (
    MODEL_VERSION,
    BoundRoleMember,
    ResolvedOperationBinding,
    ResolvedRoleBinding,
    SubjectContext,
)
from corpus_structure.semantic.identity import canonical_bytes
from corpus_structure.semantic.prepare import prepare_release
from corpus_structure.semantic.python_operation_sources import (
    ClosedPythonSources,
    PythonSource,
    PythonSourceCollection,
)
from corpus_structure.semantic.types import (
    PreparationError,
    ResolvedDependencies,
    SourceArtifact,
    SourceBundle,
)


def contract(**changes: Any) -> dict[str, Any]:
    return {
        "id": "urn:test:derive",
        "profile": "derivation",
        "subject": "original-occurrence",
        "context": ["projection", "analyzed-scope"],
        "roles": [
            {
                "name": "source",
                "kind": "integer",
                "direction": "input",
                "minimum": 1,
                "maximum": 1,
                "collection": "scalar",
                "presence": "required",
                "parameter": "x",
                "support": {
                    "provenance": "exact",
                    "identity_requirements": ["episode"],
                    "source": "same-original",
                    "coverage": "selected-scope",
                },
            },
            {
                "name": "result",
                "kind": "integer",
                "direction": "output",
                "minimum": 1,
                "maximum": 1,
                "collection": "scalar",
                "presence": "required",
            },
        ],
        "applicability": ["admitted"],
        "invariants": ["exact-integer"],
        "coverage": "selected-scope",
        "outcomes": ["produced", "unknown"],
        "precision": "exact",
        "dependencies": [],
        "effects": [],
        "capabilities": {
            "forms": ["scalar"],
            "preparation": "none",
            "cancellation": "call-boundary",
            "ownership": "immutable",
        },
        "behavior": "integer-derive-v1",
        "parameters": {},
        "binding": {"operator": "scan", "roles": ["source"]},
        **changes,
    }


def declarations(*operations: dict, kinds: list | None = None) -> tuple[SourceArtifact, ...]:
    return (
        SourceArtifact(
            "operations.yaml",
            canonical_bytes(
                {"version": MODEL_VERSION, "operations": operations, "kinds": kinds or []}
            ),
        ),
    )


def python_inputs(code: str, module: str = "example", *, boundaries=()) -> PythonSourceCollection:
    return PythonSourceCollection(
        (PythonSource(module, code.encode(), module + ".py"),), boundary_contracts=boundaries
    )


def operation_source(body="return helper(x)", *, extra="", metadata=None) -> str:
    return (
        "raise RuntimeError('target modules must never execute')\nGLOBAL = 3\n"
        "def helper(x: int) -> int:\n    return x + GLOBAL\n"
        f"def derive(x: int = 2) -> int:\n    {body}\n"
        f"derive__data_operation__ = {metadata or contract()!r}\n{extra}"
    )


def identity(model, owner="urn:test:derive", domain="recipe"):
    return next(
        item.key for item in model.identities if item.owner == owner and item.domain == domain
    )


def test_declaration_and_closed_python_share_effective_domain_contract():
    declared = compile_data_operations(declarations=declarations(contract()))
    extracted = compile_data_operations(python_sources=python_inputs(operation_source()))
    left, right = declared.operations[0], extracted.operations[0]
    assert left.roles == right.roles
    assert left.recipe == right.recipe
    assert right.callable_surfaces[0].parameters[0].default == "2"
    assert right.callable_surfaces[0].parameters[0].annotation == "int"
    assert {node.id for node in extracted.implementation_slices[0].nodes} == {
        "python:example.derive",
        "python:example.helper",
        "python:example.GLOBAL",
        "interpretation:closed-python-operations-v1",
    }
    assert extracted.implementation_slices[0].complete
    assert identity(extracted, "python:example.derive", "implementation-slice").startswith(
        "implementation-slice:"
    )
    exported = json.loads(extracted.content)
    assert exported["operations"][0]["origins"][0]["category"] == "authored"
    assert exported["identities"]


def test_slice_is_local_to_required_definitions_and_ignores_formatting():
    baseline = compile_data_operations(python_sources=python_inputs(operation_source()))
    unrelated = compile_data_operations(
        python_sources=python_inputs(operation_source(extra="def unrelated(): return 99\n"))
    )
    formatted = compile_data_operations(
        python_sources=python_inputs(
            operation_source().replace("return x + GLOBAL", "return   x+GLOBAL  # unchanged syntax")
        )
    )
    changed = compile_data_operations(
        python_sources=python_inputs(
            operation_source().replace("return x + GLOBAL", "return x - GLOBAL")
        )
    )
    default = compile_data_operations(
        python_sources=python_inputs(operation_source().replace("x: int = 2", "x: int = 4"))
    )
    assert identity(baseline) == identity(unrelated) == identity(formatted)
    assert identity(changed) != identity(baseline) != identity(default)
    assert identity(changed, domain="definition") == identity(baseline, domain="definition")


def test_import_aliases_reexports_and_inherited_public_ownership_are_closed():
    metadata = contract(entrypoints=["run"])
    code = (
        "from dep.api import exposed as helper\n"
        "class Base:\n    delta=3\n    def run(self, x: int) -> int: return helper(x)+self.delta\n"
        "class Child(Base):\n    delta=4\n"
        f"Child.__data_operation__={metadata!r}\n"
    )
    sources = PythonSourceCollection(
        (
            PythonSource("application", code.encode(), "application.py"),
            PythonSource("dep.api", b"from .impl import plus as exposed\n", "dep/api.py"),
            PythonSource("dep.impl", b"def plus(x: int) -> int: return x+1\n", "dep/impl.py"),
        )
    )
    model = compile_data_operations(python_sources=sources)
    surface = model.operations[0].callable_surfaces[0]
    assert (surface.exposed, surface.declaration) == (
        "application.Child.run",
        "application.Base.run",
    )
    assert {
        "python:dep.impl.plus",
        "python:application.Child.delta",
        "python:application.Base.run",
    } <= {node.id for node in model.implementation_slices[0].nodes}
    assert model.implementation_slices[0].complete


@pytest.mark.parametrize("body", ["return getattr(x, 'method')()", "return callback(x)"])
def test_dynamic_determinants_never_gain_a_reusable_recipe(body):
    code = operation_source(body).replace("x: int = 2", "x: int = 2, callback: object = None")
    model = compile_data_operations(python_sources=python_inputs(code))
    assert not model.implementation_slices[0].complete
    assert model.implementation_slices[0].unknowns
    assert not any(item.domain == "recipe" for item in model.identities)
    assert any(item.domain == "definition" for item in model.identities)


def test_opaque_contract_requires_captured_revision_and_never_imports_target():
    metadata = contract(
        opaque=[
            {
                "reference": "missing_provider",
                "contract": "provider-rule-v1",
                "role": "semantic-algorithm",
            }
        ]
    )
    code = operation_source("return calculate(x)", metadata=metadata).replace(
        "GLOBAL = 3", "from missing_provider import calculate\nGLOBAL = 3"
    )
    missing = compile_data_operations(python_sources=python_inputs(code))
    assert any("immutable revision" in u.reason for u in missing.implementation_slices[0].unknowns)
    admitted = compile_data_operations(
        python_sources=python_inputs(
            code,
            boundaries=(
                SourceArtifact(
                    "provider-rule-v1", b"captured supported provider contract revision"
                ),
            ),
        )
    )
    assert admitted.implementation_slices[0].complete
    assert identity(admitted)
    changed = compile_data_operations(
        python_sources=python_inputs(
            code, boundaries=(SourceArtifact("provider-rule-v1", b"changed semantic rule"),)
        )
    )
    assert identity(admitted) != identity(changed)


def test_source_metadata_expressions_and_stub_disagreement_refuse():
    with pytest.raises(PreparationError, match="static literal"):
        ClosedPythonSources(
            python_inputs("def f(x:int)->int: return x\nf.__data_operation__=dict(id='x')\n")
        )
    with pytest.raises(PreparationError, match="source/stub"):
        ClosedPythonSources(
            PythonSourceCollection(
                (
                    PythonSource(
                        "m", b"def f(x:int=1)->int: return x\n", "m.py", b"def f(x:str)->int: ...\n"
                    ),
                )
            )
        )


def schema_bundle(*, minimum="0", enum_meaning="urn:meaning:first") -> SourceBundle:
    return SourceBundle(
        "model",
        (
            SourceArtifact(
                "model",
                f"""id: urn:test:model
name: model
prefixes:
  test: 'urn:test:'
  xsd: 'http://www.w3.org/2001/XMLSchema#'
default_prefix: test
types:
  integer:
    base: int
    uri: xsd:integer
  string:
    base: str
    uri: xsd:string
classes:
  Base:
    attributes:
      value:
        range: integer
        minimum_value: {minimum}
  Child:
    is_a: Base
    attributes:
      category:
        range: Category
  Other:
    attributes:
      unrelated:
        range: string
enums:
  Category:
    permissible_values:
      first:
        meaning: {enum_meaning}
""".encode(),
            ),
        ),
    )


def test_effective_kind_closure_includes_inheritance_properties_and_enum_meaning():
    a = compile_data_operations(schema_bundle())
    b = compile_data_operations(schema_bundle(minimum="2"))
    c = compile_data_operations(schema_bundle(enum_meaning="urn:meaning:changed"))
    assert identity(a, "urn:test:Child", "kind") != identity(b, "urn:test:Child", "kind")
    assert identity(a, "urn:test:Child", "kind") != identity(c, "urn:test:Child", "kind")
    assert identity(a, "urn:test:Other", "kind") == identity(b, "urn:test:Other", "kind")
    child = next(k for k in a.kinds if k.semantic_id == "urn:test:Child/property/value")
    assert json.loads(child.facts)["minimum"] == "0"


def test_discovery_aggregate_and_effectful_profiles_are_explicit():
    aggregate = contract(
        id="urn:test:aggregate",
        profile="discovery",
        binding={
            "operator": "forall",
            "roles": ["source"],
            "population": "authored-population-v1",
            "children": [{"operator": "scan", "roles": ["source"]}],
        },
    )
    command = contract(
        id="urn:test:publish",
        profile="command",
        dependencies=["urn:test:aggregate"],
        effects=[
            {
                "name": "publish",
                "authorization": ["owned-attempt"],
                "idempotency": "exact-fenced-replay",
                "fulfillment": "receipt",
            }
        ],
        state_dimensions=[{"name": "state", "values": ["owned", "published"]}],
        transitions=[
            {
                "dimension": "state",
                "before": "owned",
                "after": "published",
                "outcome": "produced",
                "effects": ["publish"],
            }
        ],
    )
    model = compile_data_operations(declarations=declarations(aggregate, command))
    assert {operation.profile for operation in model.operations} == {"discovery", "command"}
    assert model.operation("urn:test:publish").effects[0].fulfillment == "receipt"
    assert any(edge.relation == "operation_dependency" for edge in model.edges)


@pytest.mark.parametrize(
    "change, message",
    [
        ({"dependencies": ["urn:missing"]}, "unresolved"),
        ({"binding": {"operator": "sql", "value": "select 1"}}, "unsupported relational"),
        ({"binding": {"operator": "absent", "roles": ["source"]}}, "closed population"),
        (
            {
                "effects": [
                    {
                        "name": "write",
                        "authorization": ["role"],
                        "idempotency": "once",
                        "fulfillment": "receipt",
                    }
                ]
            },
            "command profile",
        ),
    ],
)
def test_invalid_contracts_are_located(change, message):
    with pytest.raises(PreparationError, match=message) as error:
        compile_data_operations(declarations=declarations(contract(**change)))
    assert error.value.diagnostics[0].location


def test_operation_cycles_and_duplicate_roles_refuse():
    with pytest.raises(PreparationError, match="unsupported cycle"):
        compile_data_operations(
            declarations=declarations(
                contract(dependencies=["urn:test:other"]),
                contract(id="urn:test:other", dependencies=["urn:test:derive"]),
            )
        )
    value = contract()
    value["roles"].append(value["roles"][0])
    with pytest.raises(PreparationError, match="duplicate semantic role"):
        compile_data_operations(declarations=declarations(value))


def resolved_binding(model, *, episodes=("episode-a",), witness=None):
    member = BoundRoleMember(
        "product:one",
        identity(model, "primitive:integer", "kind"),
        "subject:one",
        "original:one",
        canonical_bytes({"start": 1, "end": 2}),
        canonical_bytes({"complete": True}),
        episodes,
        canonical_bytes({"authority": "selected"}),
    )
    return ResolvedOperationBinding(
        "urn:test:derive",
        "subject:one",
        (ResolvedRoleBinding("source", "present", (member,), witness),),
        canonical_bytes(semantic_value({})),
        "inference:one",
        canonical_bytes({"permission": "admitted"}),
        canonical_bytes({"trust": "selected"}),
        "execution:one",
        subject_context=SubjectContext(
            "project:test", "subject:one", "original:one", b'{"start":1,"end":2}'
        ),
    )


def test_compiled_policies_project_exact_and_substitutable_support_and_witnesses():
    exact = compile_data_operations(declarations=declarations(contract()))
    a = resolved_binding(exact)
    b = resolved_binding(exact, episodes=("episode-b",))
    key_a, admission_a = project_operation_binding(exact, a)
    key_b, admission_b = project_operation_binding(exact, b)
    assert key_a.identity != key_b.identity and admission_a.identity != admission_b.identity
    value = contract()
    value["roles"][0]["support"]["provenance"] = "value_substitution"
    value["roles"][0]["support"]["identity_requirements"] = []
    substitutable = compile_data_operations(declarations=declarations(value))
    key_a, admission_a = project_operation_binding(substitutable, resolved_binding(substitutable))
    key_b, admission_b = project_operation_binding(
        substitutable, resolved_binding(substitutable, episodes=("episode-b",))
    )
    assert key_a.identity == key_b.identity and admission_a.identity != admission_b.identity
    key_c, _ = project_operation_binding(
        substitutable,
        resolved_binding(
            substitutable,
            witness=canonical_bytes(
                {
                    "identity": "population:stable",
                    "complete": True,
                    "members": ["one", "two"],
                    "evidence": {"derivation_id": "population-episode"},
                }
            ),
        ),
    )
    assert key_c.identity != key_a.identity
    trusted = replace(
        resolved_binding(substitutable), trust_evidence=canonical_bytes({"trust": "different"})
    )
    trusted_key, trusted_admission = project_operation_binding(substitutable, trusted)
    assert (
        trusted_key.identity == key_a.identity
        and trusted_admission.identity != admission_a.identity
    )


def test_replicate_is_selected_by_compiled_policy():
    model = compile_data_operations(
        declarations=declarations(contract(replicate_policy="explicit-replicates"))
    )
    binding = resolved_binding(model)
    with pytest.raises(PreparationError, match="replicate"):
        project_operation_binding(model, binding)
    first, _ = project_operation_binding(model, replace(binding, replicate="first"))
    second, _ = project_operation_binding(model, replace(binding, replicate="second"))
    assert first.identity != second.identity


def test_preparation_archives_effective_products_only_when_explicitly_supplied():
    bundle = schema_bundle()
    old = prepare_release(bundle)
    deps = data_operation_dependencies(ResolvedDependencies(), declarations(contract()))
    prepared = prepare_release(bundle, deps)
    artifact = next(a for a in prepared.artifacts if a.kind == "data_operations.json")
    assert json.loads(artifact.content)["version"] == MODEL_VERSION
    assert prepared.release_id != old.release_id
    assert not any(a.kind == "data_operations.json" for a in old.artifacts)
    assert prepare_release(bundle).release_id == old.release_id
    bad = replace(
        deps, artifacts=(*deps.artifacts, SourceArtifact("data-operations/extra", b"unlisted"))
    )
    with pytest.raises(ValueError, match="differs from manifest"):
        prepare_release(bundle, bad)


def test_real_score_and_inherited_interpretation_family_have_owned_facts():
    root = Path(__file__).parents[2] / "src/corpus_structure"
    score = root / "semantic/operation_policy.py"
    score_model = compile_data_operations(
        python_sources=PythonSourceCollection(
            (
                PythonSource(
                    "corpus_structure.semantic.operation_policy", score.read_bytes(), str(score)
                ),
            )
        )
    )
    operation = score_model.operations[0]
    assert operation.semantic_id == "urn:corpus:operation:score-operation-event"
    assert [p.name for p in operation.callable_surfaces[0].parameters] == [
        "parameters",
        "features",
        "corpus_id",
        "event_version",
        "producer_version",
        "event",
    ]
    assert any(
        kind.semantic_id == "urn:corpus:kind:operation-event-parameters"
        for kind in score_model.kinds
    )
    assert not score_model.implementation_slices[
        0
    ].complete  # no invented provider contract revisions
    source = root / "methods/interpretations.py"
    family = compile_data_operations(
        python_sources=PythonSourceCollection(
            (
                PythonSource(
                    "corpus_structure.methods.interpretations", source.read_bytes(), str(source)
                ),
            )
        )
    )
    assert {op.semantic_id for op in family.operations} == {
        "urn:corpus:operation:interpret-terminology",
        "urn:corpus:operation:interpret-measurement",
        "urn:corpus:operation:author-source-records",
    }
    assert all(not implementation.complete for implementation in family.implementation_slices)
    assert not any(item.domain == "recipe" for item in family.identities)
    measurement = family.operation("urn:corpus:operation:interpret-measurement")
    run = next(s for s in measurement.callable_surfaces if s.exposed.endswith(".run"))
    assert run.declaration.endswith("TerminologyInterpretationMethod.run")
    assert run.exposed.endswith("MeasurementInterpretationMethod.run")
    assert next(o for o in measurement.origins if o.field == "coverage").declaration.endswith(
        "_AuthoredSourceMethod"
    )


def test_target_composed_preparation_never_enters_legacy_approval(monkeypatch):
    from corpus_structure.semantic import contracts
    from corpus_structure.semantic.types import PreparationProfile

    def forbidden():
        pytest.fail("target preparation imported legacy approved implementations")

    monkeypatch.setattr(contracts, "approved_implementations", forbidden)
    deps = data_operation_dependencies(ResolvedDependencies(), declarations(contract()))
    target = prepare_release(
        schema_bundle(), deps, profile=PreparationProfile(version="semantic-2")
    )
    assert target.execution_model_id is None
    assert any(artifact.kind == "data_operations.json" for artifact in target.artifacts)
    with pytest.raises(ValueError, match="cannot combine legacy"):
        data_operation_dependencies(
            ResolvedDependencies((SourceArtifact("execution/manifest.json", b"{}"),)),
            declarations(contract()),
        )


@pytest.mark.parametrize("kind_id", ["urn:test:derive", "urn:test:derive/binding"])
def test_global_semantic_identity_collisions_refuse_before_insertion(kind_id):
    with pytest.raises(PreparationError, match="collides"):
        compile_data_operations(
            declarations=declarations(contract(), kinds=[{"id": kind_id, "primitive": "integer"}])
        )


def test_class_decorator_and_default_factory_dependencies_are_never_omitted():
    metadata = contract(entrypoints=["run"])
    code = (
        "def decorate(cls): return cls\ndef factory(): return 3\n"
        "@decorate\nclass Owner:\n    option=factory()\n"
        "    def run(self, x:int)->int: return x\n"
        f"Owner.__data_operation__={metadata!r}\n"
    )
    model = compile_data_operations(python_sources=python_inputs(code))
    implementation = model.implementation_slices[0]
    assert {"python:example.decorate", "python:example.factory"} <= {
        node.id for node in implementation.nodes
    }
    assert not implementation.complete
    assert any("class decorator" in item.reason for item in implementation.unknowns)


def test_missing_inherited_python_kind_does_not_issue_kind_or_recipe_identity():
    value = contract()
    kind_declarations = [{"id": "urn:test:input", "python": "example.Input"}]
    value["roles"][0]["kind"] = "urn:test:input"
    sources = python_inputs("from absent import Base\nclass Input(Base):\n    local:int\n")
    model = compile_data_operations(
        declarations=declarations(value, kinds=kind_declarations), python_sources=sources
    )
    kind = next(kind for kind in model.kinds if kind.semantic_id == "urn:test:input")
    assert not kind.complete and "inherited kind base" in kind.unknowns[0].reason
    assert not any(
        item.owner == "urn:test:input" and item.domain == "kind" for item in model.identities
    )
    assert not any(
        item.owner == "urn:test:derive" and item.domain == "recipe" for item in model.identities
    )


@pytest.mark.parametrize("initializer", ["list()", "bytearray()", "dict()", "[1]", "(1, [])"])
def test_mutable_captured_global_constructors_cannot_be_complete(initializer):
    code = operation_source("return len(STATE)").replace("GLOBAL = 3", "STATE=" + initializer)
    model = compile_data_operations(python_sources=python_inputs(code))
    assert not model.implementation_slices[0].complete
    assert any(
        "not known immutable" in item.reason for item in model.implementation_slices[0].unknowns
    )


def test_conditional_rule_and_class_interpretation_policy_change_kind_identity():
    from .test_conditional_rules import bundle, schema

    a = schema()
    b = schema()
    b["classes"]["Thing"]["rules"][0]["preconditions"]["slot_conditions"]["status"][
        "equals_string"
    ] = "changed"
    c = schema()
    c["classes"]["Thing"]["annotations"] = {"cs:case": "casefold"}
    first = compile_data_operations(bundle(a))
    assert identity(first, "https://example.org/Thing", "kind") != identity(
        compile_data_operations(bundle(b)), "https://example.org/Thing", "kind"
    )
    assert identity(first, "https://example.org/Thing", "kind") != identity(
        compile_data_operations(bundle(c)), "https://example.org/Thing", "kind"
    )


def test_closed_population_and_provider_identity_requirements_come_from_contract():
    value = contract(
        binding={
            "operator": "forall",
            "roles": ["source"],
            "population": "all-members",
            "children": [{"operator": "scan", "roles": ["source"]}],
        }
    )
    value["roles"][0]["support"]["identity_requirements"] = ["episode", "provider", "alternative"]
    model = compile_data_operations(declarations=declarations(value))
    binding = resolved_binding(model)
    member = replace(
        binding.roles[0].members[0],
        provider_identity="provider:a",
        alternative_identity="alternative:a",
    )
    role = replace(binding.roles[0], members=(member,))
    with pytest.raises(PreparationError, match="population witness"):
        project_operation_binding(model, replace(binding, roles=(role,)))
    role = replace(
        role,
        population_witness=canonical_bytes(
            {
                "identity": "population:stable",
                "complete": True,
                "members": ["one"],
                "evidence": {"derivation_id": "population-episode"},
            }
        ),
    )
    first, _ = project_operation_binding(model, replace(binding, roles=(role,)))
    changed = replace(role, members=(replace(member, provider_identity="provider:b"),))
    second, _ = project_operation_binding(model, replace(binding, roles=(changed,)))
    assert first.identity != second.identity


def test_archived_model_is_read_without_reopening_source_or_current_defaults():
    from corpus_structure.semantic.data_operation_model import read_effective_data_operations

    model = compile_data_operations(python_sources=python_inputs(operation_source()))
    archived = read_effective_data_operations(model.content)
    assert archived == model
    record = json.loads(model.content)
    del record["operations"][0]["replicate_policy"]
    with pytest.raises(Exception, match=r"structuring|archived"):
        read_effective_data_operations(canonical_bytes(record))


def test_current_execution_schema_uses_the_pure_effective_phase(monkeypatch):
    from corpus_structure.semantic import contracts

    monkeypatch.setattr(
        contracts, "approved_implementations", lambda: pytest.fail("legacy approval invoked")
    )
    model = compile_data_operations(contracts.trusted_execution_schema())
    assert len([kind for kind in model.kinds if kind.category == "class"]) > 100
    assert any(kind.name == "OperationContract" for kind in model.kinds)
    assert all(kind.complete for kind in model.kinds)


def test_current_statistics_kind_closure_uses_supplied_terminology_bytes(monkeypatch):
    from corpus_structure.schema.pack import DOMAINS
    from corpus_structure.semantic import contracts
    from corpus_structure.semantic.prepare import (
        _view_and_vocabularies,
        effective_class_definitions,
    )
    from corpus_structure.semantic.terminology import acquire_terminology
    from corpus_structure.semantic.types import PreparationProfile

    monkeypatch.setattr(
        contracts, "approved_implementations", lambda: pytest.fail("legacy approval invoked")
    )
    pack = DOMAINS / "statistics"
    root = Path(__file__).parents[2] / "src/corpus_structure"
    terminology, assets, ontology_names = acquire_terminology(pack)
    bundle = SourceBundle(
        "statistics_semantic",
        (
            SourceArtifact("statistics_semantic", (pack / "semantic.yaml").read_bytes()),
            SourceArtifact("semantic_core", (root / "model/semantic/core.yaml").read_bytes()),
            *terminology,
        ),
    )
    from corpus_structure.semantic.observations import observation_inputs

    bundle = observation_inputs(
        bundle, model_content=(root / "model/semantic/observations.yaml").read_bytes()
    )
    dependencies = ResolvedDependencies(assets, (), ontology_names)
    profile = PreparationProfile(version="semantic-2")
    view, vocabularies, _ = _view_and_vocabularies(bundle, dependencies, profile)
    definitions = effective_class_definitions(view, profile, (item.enum for item in vocabularies))
    model = compile_data_operations(bundle, definitions=definitions, vocabularies=vocabularies)
    assert any(
        kind.name == "StatisticalDistributionFamily" and kind.category == "enum"
        for kind in model.kinds
    )
    assert any(kind.name == "MeasurementValueRole" for kind in model.kinds)
    assert all(kind.complete for kind in model.kinds)


@pytest.mark.parametrize(
    "body, extra_parameter",
    [
        ("return callbacks[0](x)", ", callbacks: tuple = ()"),
        ("return (lambda value: value)(x)", ""),
        ("return MISSING_GLOBAL(x)", ""),
        ("return MISSING_GLOBAL + x", ""),
        ("return reader(x, 'value')", ""),
        ("return max((x, 1), key=callback)", ", callback: object = None"),
    ],
)
def test_unsupported_call_categories_and_unresolved_names_withhold_recipe(body, extra_parameter):
    code = operation_source(body, extra="")
    if "reader" in body:
        code = "reader=getattr\n" + code
    code = code.replace("x: int = 2", "x: int = 2" + extra_parameter)
    model = compile_data_operations(python_sources=python_inputs(code))
    assert not model.implementation_slices[0].complete
    assert not any(item.domain == "recipe" for item in model.identities)


def test_bound_callable_name_does_not_replace_a_canonical_implementation_input():
    metadata = contract(bound_inputs=["callback"])
    code = operation_source("return callback(x)", metadata=metadata).replace(
        "x: int = 2", "x: int = 2, callback: object = None"
    )
    model = compile_data_operations(python_sources=python_inputs(code))
    assert not model.implementation_slices[0].complete
    assert not any(item.domain == "recipe" for item in model.identities)


def test_duplicate_nested_python_metadata_fields_refuse():
    code = "def f(x:int)->int: return x\nf.__data_operation__={'id':'first', 'id':'second'}\n"
    with pytest.raises(PreparationError, match="duplicate semantic metadata field"):
        ClosedPythonSources(python_inputs(code))
    with pytest.raises(PreparationError, match="duplicate semantic metadata field"):
        ClosedPythonSources(
            python_inputs(
                code.replace("'id':'first', 'id':'second'", "'nested':{'value':1,'value':2}")
            )
        )


def test_effective_python_kind_uses_c3_owner_in_diamond():
    sources = python_inputs(
        "class A:\n    x:int=1\nclass B(A): pass\nclass C(A):\n    x:int=2\nclass D(B,C): pass\n"
    )
    value = contract()
    value["roles"][0]["kind"] = "urn:test:diamond"
    model = compile_data_operations(
        declarations=declarations(value, kinds=[{"id": "urn:test:diamond", "python": "example.D"}]),
        python_sources=sources,
    )
    kind = next(item for item in model.kinds if item.semantic_id == "urn:test:diamond")
    field = next(
        field
        for field in json.loads(kind.facts)["effective_python"]["fields"]
        if field["name"] == "x"
    )
    assert field["owner"] == "example.C.x" and field["default"] == "2"
    assert kind.complete
    assert identity(model, "urn:test:diamond", "kind")


@pytest.mark.parametrize("literal", ["wrong-type", -1])
def test_literal_predicates_use_production_effective_field_constraints(literal):
    value = contract()
    value["roles"][0]["kind"] = "urn:test:Base"
    value["binding"] = {
        "operator": "literal",
        "fields": [{"role": "source", "projection": "urn:test:Base", "field": "value"}],
        "value": literal,
    }
    with pytest.raises(PreparationError, match="typed binding literal"):
        compile_data_operations(schema_bundle(), declarations(value))
    value["binding"]["value"] = 2
    assert identity(compile_data_operations(schema_bundle(), declarations(value)))


def test_asset_digests_and_missing_concepts_population_refuse():
    value = contract(
        assets=[
            {
                "reference": "asset",
                "contract": "asset-v1",
                "role": "semantic-model",
                "content_digest": "mutable-path",
            }
        ]
    )
    with pytest.raises(PreparationError, match="invalid captured semantic asset"):
        compile_data_operations(declarations=declarations(value))
    bundle = schema_bundle()
    source = bundle.sources[0].content.replace(
        b"  Category:\n    permissible_values:",
        b"  Category:\n    concepts: [urn:test:concept]\n    permissible_values:",
    )
    with pytest.raises(PreparationError, match="effective vocabulary"):
        compile_data_operations(replace(bundle, sources=(SourceArtifact("model", source),)))


def test_astroid_structural_binding_context_is_closed_and_isolated(monkeypatch):
    import astroid
    import astroid.manager
    import astroid.nodes

    before = dict(astroid.MANAGER.astroid_cache)

    def forbidden(*args, **kwargs):
        pytest.fail("source analysis escaped into ambient module lookup or inference")

    monkeypatch.setattr(astroid.manager.AstroidManager, "ast_from_module_name", forbidden)
    monkeypatch.setattr(astroid.nodes.Name, "infer", forbidden)
    first = compile_data_operations(
        python_sources=python_inputs(operation_source(extra="alias=helper\n"))
    )
    changed = compile_data_operations(
        python_sources=python_inputs(operation_source().replace("GLOBAL = 3", "GLOBAL = 5"))
    )
    again = compile_data_operations(
        python_sources=python_inputs(operation_source(extra="alias=helper\n"))
    )
    assert identity(first) == identity(again) != identity(changed)
    assert dict(astroid.MANAGER.astroid_cache) == before
    alias = compile_data_operations(
        python_sources=python_inputs(operation_source("return alias(x)", extra="alias=helper\n"))
    )
    assert alias.implementation_slices[0].complete
    assert identity(alias)


def test_actual_claim_source_item_has_a_closed_recipe_from_the_captured_module():
    source = Path(__file__).parents[2] / "src/corpus_structure/semantic/identity.py"
    original = source.read_bytes()
    inputs = PythonSourceCollection(
        (PythonSource("corpus_structure.semantic.identity", original, str(source)),)
    )
    model = compile_data_operations(python_sources=inputs)
    operation = model.operation("urn:corpus:operation:claim-source-item")
    assert (
        operation.callable_surfaces[0].declaration
        == "corpus_structure.semantic.identity.claim_source_item"
    )
    assert model.implementation_slices[0].complete
    assert identity(model, operation.semantic_id)
    # Modify the actual captured implementation body, preserving its owned contract.
    changed = original.replace(b'return f"claims/{index}"', b'return f"claims/{index + 1}"')
    assert changed != original
    other = compile_data_operations(
        python_sources=replace(inputs, sources=(replace(inputs.sources[0], content=changed),))
    )
    assert identity(model, operation.semantic_id) != identity(other, operation.semantic_id)


def test_effective_field_shadowed_by_method_is_not_exported_from_base():
    sources = python_inputs("class A:\n    x:int=1\nclass D(A):\n    def x(self)->int: return 2\n")
    value = contract()
    value["roles"][0]["kind"] = "urn:test:shadowed"
    model = compile_data_operations(
        declarations=declarations(
            value, kinds=[{"id": "urn:test:shadowed", "python": "example.D"}]
        ),
        python_sources=sources,
    )
    kind = next(item for item in model.kinds if item.semantic_id == "urn:test:shadowed")
    assert "x" not in {
        field["name"] for field in json.loads(kind.facts)["effective_python"]["fields"]
    }


@pytest.mark.parametrize("assignments", ["STATE=STATE", "STATE=OTHER\nOTHER=STATE"])
def test_alias_cycles_have_no_closed_immutable_terminal(assignments):
    model = compile_data_operations(
        python_sources=python_inputs(
            operation_source("return len(STATE)").replace("GLOBAL = 3", assignments)
        )
    )
    assert not model.implementation_slices[0].complete
    assert not any(item.domain == "recipe" for item in model.identities)


def test_function_decorator_cannot_silently_change_the_extracted_surface():
    code = operation_source().replace("def derive(", "@decorate\ndef derive(")
    code = "def decorate(function): return function\n" + code
    model = compile_data_operations(python_sources=python_inputs(code))
    assert not model.implementation_slices[0].complete
    assert any(
        "callable-surface transformation" in item.reason
        for item in model.implementation_slices[0].unknowns
    )
    assert not any(item.domain == "recipe" for item in model.identities)


@pytest.mark.parametrize("builtin", ["max", "min"])
@pytest.mark.parametrize("aliased", [False, True])
def test_expanded_builtin_callback_options_withhold_recipe(builtin, aliased):
    target = "choose" if aliased else builtin
    extra = f"choose={builtin}\n" if aliased else ""
    code = operation_source(f"return {target}((x, 1), **options)", extra=extra)
    code = code.replace("x: int = 2", "x: int = 2, options: dict = None")
    model = compile_data_operations(python_sources=python_inputs(code))
    implementation = model.implementation_slices[0]
    assert not implementation.complete
    assert any("expanded keyword call arguments" in item.reason for item in implementation.unknowns)
    assert not any(item.domain == "recipe" for item in model.identities)


@pytest.mark.parametrize("reexport", [False, True])
@pytest.mark.parametrize("arguments", ["**options", "key=callback"])
def test_imported_builtin_alias_callback_arguments_remain_unsupported(reexport, arguments):
    declaration = "from exports import choose" if reexport else "from helpers import choose"
    code = operation_source(f"return choose((x, 1), {arguments})")
    code = declaration + "\n" + code
    code = code.replace("x: int = 2", "x: int = 2, options: dict = None, callback: object = None")
    sources = [
        PythonSource("example", code.encode(), "example.py"),
        PythonSource("helpers", b"choose=max\n", "helpers.py"),
    ]
    if reexport:
        sources.append(PythonSource("exports", b"from helpers import choose\n", "exports.py"))
    model = compile_data_operations(python_sources=PythonSourceCollection(tuple(sources)))
    assert not model.implementation_slices[0].complete
    assert not any(item.domain == "recipe" for item in model.identities)


def test_population_receipt_and_trust_do_not_salt_value_substitutable_request_identity():
    value = contract()
    value["roles"][0]["support"]["provenance"] = "value_substitution"
    value["roles"][0]["support"]["identity_requirements"] = []
    model = compile_data_operations(declarations=declarations(value))
    witness = {
        "identity": "population:stable",
        "complete": True,
        "members": ["one"],
        "evidence": {
            "population_id": "receipt:a",
            "derivation_id": "episode:a",
            "trust_snapshot": {"scope": 1},
        },
    }
    first, first_admission = project_operation_binding(
        model, resolved_binding(model, witness=canonical_bytes(witness))
    )
    revised = {
        **witness,
        "evidence": {
            "population_id": "receipt:b",
            "derivation_id": "episode:b",
            "trust_snapshot": {"scope": 2},
        },
    }
    second, second_admission = project_operation_binding(
        model, resolved_binding(model, witness=canonical_bytes(revised))
    )
    assert first.identity == second.identity
    assert first_admission.identity != second_admission.identity
    assert first.inputs["source"]["population_witness"] == {
        "identity": "population:stable",
        "complete": True,
        "members": ("one",),
    }
    exact = compile_data_operations(declarations=declarations(contract()))
    exact_first, _ = project_operation_binding(
        exact, resolved_binding(exact, witness=canonical_bytes(witness))
    )
    exact_second, _ = project_operation_binding(
        exact, resolved_binding(exact, witness=canonical_bytes(revised))
    )
    assert exact_first.identity != exact_second.identity


def test_nonsequence_request_positions_exclude_incidental_producing_ordinals():
    value = contract()
    value["roles"][0]["support"]["provenance"] = "value_substitution"
    value["roles"][0]["support"]["identity_requirements"] = []
    for collection in ("scalar", "set", "bag", "sequence"):
        value["roles"][0]["collection"] = collection
        model = compile_data_operations(declarations=declarations(value))
        binding = resolved_binding(model)
        member = binding.roles[0].members[0]
        first_binding = replace(
            binding, roles=(replace(binding.roles[0], members=(replace(member, position=0),)),)
        )
        second_binding = replace(
            binding, roles=(replace(binding.roles[0], members=(replace(member, position=7),)),)
        )
        first, first_admission = project_operation_binding(model, first_binding)
        second, second_admission = project_operation_binding(model, second_binding)
        if collection == "sequence":
            assert first.identity != second.identity
        else:
            assert first.identity == second.identity
        assert first_admission.identity != second_admission.identity


def test_authored_kind_native_policies_are_explicit_canonical_and_fingerprinted():
    value = contract()
    value["roles"][0]["kind"] = "urn:protected"
    ordinary = {"id": "urn:protected", "primitive": "integer"}
    protected = {
        **ordinary,
        "universe": "evaluator",
        "projection_families": ["coverage", "coordinate"],
    }
    default_model = compile_data_operations(declarations=declarations(value, kinds=[ordinary]))
    model = compile_data_operations(declarations=declarations(value, kinds=[protected]))
    permuted = compile_data_operations(
        declarations=declarations(
            value, kinds=[{**protected, "projection_families": ["coordinate", "coverage"]}]
        )
    )
    facts = json.loads(
        next(kind.facts for kind in model.kinds if kind.semantic_id == "urn:protected")
    )
    assert facts["universe"] == "evaluator"
    assert facts["projection_families"] == ["coordinate", "coverage"]
    defaults = json.loads(
        next(kind.facts for kind in default_model.kinds if kind.semantic_id == "urn:protected")
    )
    assert defaults["universe"] == "ordinary" and defaults["projection_families"] == []
    assert identity(model, "urn:protected", "kind") != identity(
        default_model, "urn:protected", "kind"
    )
    assert identity(model, "urn:protected", "kind") == identity(permuted, "urn:protected", "kind")


@pytest.mark.parametrize(
    "policy",
    [
        {"universe": "public"},
        {"universe": None},
        {"universe": ["ordinary"]},
        {"projection_families": "coverage"},
        {"projection_families": None},
        {"projection_families": ["unknown"]},
        {"projection_families": ["coverage", "coverage"]},
        {"projection_families": [False]},
    ],
)
def test_authored_kind_native_policy_unknown_or_ambiguous_variants_refuse(policy):
    with pytest.raises(PreparationError, match=r"universe|projection_families"):
        compile_data_operations(
            declarations=declarations(
                contract(), kinds=[{"id": "urn:protected", "primitive": "integer", **policy}]
            )
        )


def annotated_policy_schema(universe="source", families='["coverage", "coordinate"]'):
    bundle = schema_bundle()
    source = bundle.sources[0]
    annotations = (
        f"    annotations:\n      cs:data_universe: '{universe}'\n"
        f"      cs:projection_families: '{families}'\n"
    )
    return replace(
        bundle,
        sources=(
            replace(
                source,
                content=source.content.replace(b"  Base:\n", ("  Base:\n" + annotations).encode()),
            ),
        ),
    )


def test_linkml_kind_native_policies_survive_safe_annotation_and_reach_property_facts():
    model = compile_data_operations(annotated_policy_schema())
    permuted = compile_data_operations(
        annotated_policy_schema(families='[ "coordinate", "coverage" ]')
    )
    ordinary = compile_data_operations(schema_bundle())
    for owner in ("urn:test:Base", "urn:test:Base/property/value"):
        facts = json.loads(next(kind.facts for kind in model.kinds if kind.semantic_id == owner))
        assert facts["universe"] == "source"
        assert facts["projection_families"] == ["coordinate", "coverage"]
        assert identity(model, owner, "kind") != identity(ordinary, owner, "kind")
        assert identity(model, owner, "kind") == identity(permuted, owner, "kind")
    changed = compile_data_operations(annotated_policy_schema(universe="evaluator"))
    assert identity(changed, "urn:test:Base", "kind") != identity(model, "urn:test:Base", "kind")


@pytest.mark.parametrize(
    "universe,families",
    [
        ("public", "[]"),
        ("ordinary", "not-json"),
        ("source", '"coverage"'),
        ("evaluator", '["coordinate","coordinate"]'),
        ("ordinary", '["not-a-family"]'),
    ],
)
def test_linkml_kind_native_policy_invalid_values_refuse(universe, families):
    with pytest.raises(PreparationError, match=r"universe|projection_families"):
        compile_data_operations(annotated_policy_schema(universe, families))


def test_native_policy_annotations_do_not_silently_apply_to_properties():
    bundle = schema_bundle()
    source = bundle.sources[0]
    content = source.content.replace(
        b"      value:\n",
        b"      value:\n        annotations:\n          cs:data_universe: evaluator\n",
    )
    with pytest.raises(PreparationError, match="policies belong to classes"):
        compile_data_operations(replace(bundle, sources=(replace(source, content=content),)))


def test_json_schema_property_projection_inherits_its_explicit_kind_policy():
    value = contract()
    value["roles"][0]["kind"] = "urn:projected"
    kind = {
        "id": "urn:projected",
        "universe": "source",
        "projection_families": ["endpoint", "role"],
        "json_schema": {
            "type": "object",
            "properties": {"value": {"type": "integer"}},
            "required": ["value"],
            "additionalProperties": False,
        },
    }
    model = compile_data_operations(declarations=declarations(value, kinds=[kind]))
    prop = json.loads(
        next(
            item.facts for item in model.kinds if item.semantic_id == "urn:projected/property/value"
        )
    )
    assert prop["universe"] == "source" and prop["projection_families"] == ["endpoint", "role"]


def test_subject_association_is_owned_typed_semantic_role_meaning():
    from corpus_structure.semantic.data_operation_model import read_effective_data_operations

    value = contract()
    value["roles"][0].update(kind="Other", subject_field="unrelated")
    compiled = compile_data_operations(schema_bundle(), declarations=declarations(value))
    assert compiled.operations[0].roles[0].subject_field == "unrelated"
    assert read_effective_data_operations(compiled.content).content == compiled.content
    unchanged = contract()
    unchanged["roles"][0]["kind"] = "Other"
    baseline = compile_data_operations(schema_bundle(), declarations=declarations(unchanged))
    assert identity(compiled) != identity(baseline)
    value["roles"][0]["subject_field"] = "undeclared"
    with pytest.raises(PreparationError, match="owned kind property"):
        compile_data_operations(schema_bundle(), declarations=declarations(value))
    value["roles"][0].update(kind="Base", subject_field="value")
    with pytest.raises(PreparationError, match="scalar subject identifier"):
        compile_data_operations(schema_bundle(), declarations=declarations(value))


def test_source_set_policy_is_owned_typed_and_part_of_definition():
    from corpus_structure.semantic.data_operation_model import read_effective_data_operations

    value = contract()
    value["roles"][0]["kind"] = "Other"
    baseline = compile_data_operations(schema_bundle(), declarations=declarations(value))
    support = value["roles"][0]["support"]
    support.update(
        source="frozen-source-set", source_set="inputs", source_reference_field="unrelated"
    )
    compiled = compile_data_operations(schema_bundle(), declarations=declarations(value))
    compiled_support = compiled.operations[0].roles[0].support
    assert compiled_support is not None
    assert compiled_support.source_set == "inputs"
    assert read_effective_data_operations(compiled.content).content == compiled.content
    assert identity(compiled) != identity(baseline)
    support["source_reference_field"] = "missing"
    with pytest.raises(PreparationError, match="owned scalar"):
        compile_data_operations(schema_bundle(), declarations=declarations(value))
    support.pop("source_reference_field")
    with pytest.raises(PreparationError, match="explicit owned"):
        compile_data_operations(schema_bundle(), declarations=declarations(value))


@pytest.mark.parametrize(
    "body,extra",
    [
        ("return derive.__code__.co_firstlineno", ""),
        ("alias = derive\n    return alias.__code__.co_firstlineno", ""),
        ("return alias.__code__.co_firstlineno", "alias=derive\n"),
        ("return helper(x)", "def helper(x): return derive.__code__.co_firstlineno\n"),
        ("return str(derive)", ""),
        ("return str(produce())", "def produce(): return derive\n"),
        ("alias = derive.__code__\n    return alias.co_firstlineno", ""),
        ("return consume(derive)", "def consume(value): return str(value)\n"),
    ],
)
def test_observable_captured_object_access_withholds_reusable_identity(body, extra):
    source = operation_source(body, extra=extra)
    for prefix in ("", "\n\n"):
        model = compile_data_operations(python_sources=python_inputs(prefix + source))
        assert not model.implementation_slices[0].complete
        assert not any(item.domain == "recipe" for item in model.identities)
        assert any(
            "attribute access" in u.reason or "escape" in u.reason
            for u in model.implementation_slices[0].unknowns
        )


def test_closed_local_helper_alias_retains_supplying_dependency():
    model = compile_data_operations(
        python_sources=python_inputs(operation_source("alias = helper\n    return alias(x)"))
    )
    assert model.implementation_slices[0].complete
    assert "python:example.helper" in {n.id for n in model.implementation_slices[0].nodes}


def test_nested_boundary_argument_does_not_authorize_outer_receiver():
    value = contract(
        opaque=[
            {"reference": "provider", "contract": "provider-rule-v1", "role": "semantic-algorithm"}
        ]
    )
    code = "import provider\n" + operation_source(
        "return factory(provider).hidden(x)",
        metadata=value,
        extra="def factory(value): return value\n",
    )
    model = compile_data_operations(
        python_sources=python_inputs(
            code, boundaries=(SourceArtifact("provider-rule-v1", b"closed-provider"),)
        )
    )
    assert not model.implementation_slices[0].complete
    assert any(
        "unsupported member dispatch" in u.reason or "attribute access" in u.reason
        for u in model.implementation_slices[0].unknowns
    )


def test_captured_callable_mutation_cannot_be_reusable():
    model = compile_data_operations(
        python_sources=python_inputs(operation_source("derive.marker = x\n    return x"))
    )
    assert not model.implementation_slices[0].complete
    assert any(
        "captured object mutation" in u.reason for u in model.implementation_slices[0].unknowns
    )


def test_nested_closed_calls_do_not_count_as_callable_escape():
    model = compile_data_operations(
        python_sources=python_inputs(operation_source("return int(helper(x))"))
    )
    assert model.implementation_slices[0].complete


def test_receiver_escape_to_builtin_observer_has_no_reusable_identity():
    metadata = contract(entrypoints=["run"])
    code = (
        "class Receiver:\n    __data_operation__ = "
        + repr(metadata)
        + "\n    def run(self, x: int) -> int:\n        return str(self)\n"
    )
    model = compile_data_operations(python_sources=python_inputs(code))
    assert not model.implementation_slices[0].complete
    assert any("escape" in u.reason for u in model.implementation_slices[0].unknowns)
    assert not any(item.domain == "recipe" for item in model.identities)
