"""Declaration vocabulary and pure DDO construction support.

Presets preserve each family's literal semantic identity, including hand-authored
compiler expectations. They do not supply independent expected results.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from functools import cache
from typing import Any

from corpus_structure.semantic.contracts import implementation_overridden
from corpus_structure.semantic.data_operation_compilation import compile_data_operations
from corpus_structure.semantic.data_operation_demands import RootSubject
from corpus_structure.semantic.data_operation_identity import semantic_value
from corpus_structure.semantic.data_operation_json import json_bytes
from corpus_structure.semantic.data_operation_model import (
    MODEL_VERSION,
    BoundRoleMember,
    ResolvedOperationBinding,
    ResolvedRoleBinding,
    SubjectContext,
)
from corpus_structure.semantic.identity import canonical_bytes
from corpus_structure.semantic.types import SourceArtifact


@dataclass(frozen=True)
class DeclarationVocabulary:
    subject: str
    context: tuple[str, ...]
    applicability: tuple[str, ...]
    invariants: tuple[str, ...]
    coverage: str
    outcomes: tuple[str, ...]
    precision: str
    cancellation: str
    ownership: str


def declaration(
    identifier, *, vocabulary, roles, behavior, parameters, **changes
) -> dict[str, Any]:
    value = {
        "id": identifier,
        "profile": "derivation",
        "subject": vocabulary.subject,
        "context": list(vocabulary.context),
        "roles": roles,
        "applicability": list(vocabulary.applicability),
        "invariants": list(vocabulary.invariants),
        "coverage": vocabulary.coverage,
        "outcomes": list(vocabulary.outcomes),
        "precision": vocabulary.precision,
        "dependencies": [],
        "effects": [],
        "capabilities": {
            "forms": ["scalar"],
            "preparation": "none",
            "cancellation": vocabulary.cancellation,
            "ownership": vocabulary.ownership,
        },
        "behavior": behavior,
        "parameters": parameters,
        "binding": {"operator": "all", "children": []},
    }
    value.update(changes)
    return value


def native_declaration(
    identifier,
    *,
    behavior,
    roles,
    outcomes,
    context,
    cancellation,
    ownership,
    preparation,
    parameters,
    **changes,
) -> dict[str, Any]:
    vocabulary = replace(
        NATIVE,
        outcomes=tuple(outcomes),
        context=tuple(context),
        cancellation=cancellation,
        ownership=ownership,
    )
    return declaration(
        identifier,
        vocabulary=vocabulary,
        roles=roles,
        behavior=behavior,
        parameters=parameters,
        capabilities={
            "forms": ["scalar"],
            "preparation": preparation,
            "cancellation": cancellation,
            "ownership": ownership,
        },
        **changes,
    )


@dataclass(frozen=True)
class DeclarationRecipe:
    content: bytes
    name: str = "ops"


def compiled(recipe: DeclarationRecipe):
    # Source/parser overrides must never consume or populate the normal memo.
    return _compile(recipe) if implementation_overridden() else _compiled(recipe)


def _compile(recipe):
    return compile_data_operations(declarations=(SourceArtifact(recipe.name, recipe.content),))


_compiled = cache(_compile)


def subject_context(*, project, subject, source, scope):
    return SubjectContext(project, subject, source, json_bytes(scope))


def root_subject(*, subject, source, scope):
    return RootSubject(subject, source, json_bytes(scope))


# Keep the family vocabulary: compiled identity expectations include these literals.
COMPILATION = DeclarationVocabulary(
    subject="original-occurrence",
    context=("projection", "analyzed-scope"),
    applicability=("admitted",),
    invariants=("exact-integer",),
    coverage="selected-scope",
    outcomes=("produced", "unknown"),
    precision="exact",
    cancellation="call-boundary",
    ownership="immutable",
)

# Keep the family vocabulary: compiled identity expectations include these literals.
DEMAND = DeclarationVocabulary(
    subject="document",
    context=(),
    applicability=("declared",),
    invariants=("integer",),
    coverage="whole",
    outcomes=("produced",),
    precision="exact",
    cancellation="call-boundary",
    ownership="immutable",
)

# Keep the family vocabulary: compiled identity expectations include these literals.
BINDING = DeclarationVocabulary(
    subject="document",
    context=(),
    applicability=(),
    invariants=(),
    coverage="complete",
    outcomes=("produced",),
    precision="exact",
    cancellation="boundary",
    ownership="immutable",
)

# Keep the family vocabulary: compiled identity expectations include these literals.
NATIVE = DeclarationVocabulary(
    subject="original-occurrence",
    context=("project", "source", "analyzed-scope"),
    applicability=("admitted",),
    invariants=("integer",),
    coverage="declared-scope",
    outcomes=("success", "empty", "failed"),
    precision="exact",
    cancellation="transaction-boundary",
    ownership="one-claim",
)


PARAMETER = DeclarationVocabulary(
    subject="source",
    context=(),
    applicability=(),
    invariants=(),
    coverage="selected",
    outcomes=("success",),
    precision="exact",
    cancellation="call-boundary",
    ownership="immutable",
)


def contract(**changes: Any) -> dict[str, Any]:
    value = declaration(
        "urn:test:derive",
        vocabulary=COMPILATION,
        roles=[
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
        behavior="integer-derive-v1",
        parameters={},
        binding={"operator": "scan", "roles": ["source"]},
    )
    value.update(changes)
    return value


def declarations(*operations: dict, kinds: list | None = None) -> tuple[SourceArtifact, ...]:
    return (
        SourceArtifact(
            "operations.yaml",
            canonical_bytes(
                {"version": MODEL_VERSION, "operations": operations, "kinds": kinds or []}
            ),
        ),
    )


def identity(model, owner="urn:test:derive", domain="recipe"):
    return next(
        item.key for item in model.identities if item.owner == owner and item.domain == domain
    )


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


def operation(name, **changes) -> dict[str, Any]:
    value = declaration(
        name,
        vocabulary=DEMAND,
        roles=[
            {
                "name": "result",
                "kind": "integer",
                "direction": "output",
                "minimum": 1,
                "maximum": 1,
                "collection": "scalar",
                "presence": "required",
            }
        ],
        behavior="integer-one-v1",
        parameters={},
        binding={"operator": "all", "children": []},
    )
    value.update(changes)
    return value


def model(*operations):
    return compiled(
        DeclarationRecipe(canonical_bytes({"version": MODEL_VERSION, "operations": operations}))
    )


def binding_declaration(identifier="urn:op", **changes) -> dict[str, Any]:
    value = declaration(
        identifier,
        vocabulary=BINDING,
        roles=[
            {
                "name": "items",
                "kind": "integer",
                "direction": "input",
                "minimum": 1,
                "maximum": 1,
                "collection": "scalar",
                "presence": "required",
                "parameter": "x",
                "support": {
                    "provenance": "exact",
                    "source": "original",
                    "coverage": "complete",
                    "identity_requirements": ["episode"],
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
        behavior="revision-1",
        parameters={},
        binding={"operator": "scan", "roles": ["items"]},
    )
    value.update(changes)
    return value


def source_declaration() -> dict[str, Any]:
    return native_declaration(
        "urn:ddo-test:source",
        behavior="native-test-source-v1",
        roles=[
            {
                "name": "result",
                "kind": "integer",
                "direction": "output",
                "minimum": 1,
                "maximum": None,
                "collection": "sequence",
                "presence": "required",
            }
        ],
        outcomes=["success", "empty", "failed"],
        context=["project", "source", "analyzed-scope"],
        cancellation="transaction-boundary",
        ownership="one-claim",
        preparation="none",
        parameters={},
    )


def _sample_declaration() -> dict[str, Any]:
    value = source_declaration()
    value["id"] = "urn:ddo-test:sample"
    value["roles"][0].update(kind="Sample", maximum=1, collection="scalar")
    return value


def _evaluator_declaration() -> dict[str, Any]:
    value = source_declaration()
    value["id"] = "urn:ddo-test:evaluator"
    value["roles"][0]["kind"] = "urn:ddo-test:evaluator-integer"
    return value


def _set_declaration() -> dict[str, Any]:
    value = source_declaration()
    value["id"] = "urn:ddo-test:set"
    value["roles"][0]["collection"] = "set"
    return value


def _consumer_declaration() -> dict[str, Any]:
    value = source_declaration()
    value["id"] = "urn:ddo-test:consumer"
    value["roles"].insert(
        0,
        {
            "name": "source",
            "kind": "Sample",
            "direction": "input",
            "minimum": 1,
            "maximum": 1,
            "collection": "scalar",
            "presence": "required",
            "support": {
                "provenance": "exact",
                "source": "same-original",
                "coverage": "selected-scope",
                "identity_requirements": ["episode"],
            },
        },
    )
    value["binding"] = {
        "operator": "range",
        "operands": [
            {
                "kind": "field",
                "value_type": "integer",
                "field": {"role": "source", "projection": "Sample", "field": "value"},
            },
            {"kind": "literal", "value_type": "integer", "value": 10},
            {"kind": "literal", "value_type": "integer", "value": 20},
        ],
    }
    return value


def _value_consumer_declaration():
    value = _consumer_declaration()
    value["id"] = "urn:ddo-test:value-consumer"
    value["dependencies"] = ["urn:ddo-test:sample"]
    value["roles"][0]["support"].update(provenance="value_substitution", identity_requirements=[])
    return value
