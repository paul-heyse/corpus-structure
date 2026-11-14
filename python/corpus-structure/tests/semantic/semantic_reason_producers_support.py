"""Shared controlled inputs and builders for semantic reason producers support."""

from functools import cache
from pathlib import Path

from corpus_structure.semantic import (
    PreparationProfile,
    ResolvedDependencies,
    SourceArtifact,
    SourceBundle,
    prepare_release,
)
from corpus_structure.semantic.analytical_profile import analytical_inputs
from corpus_structure.semantic.composed import composed_dependencies
from corpus_structure.semantic.domain_operations import domain_rule_inputs
from corpus_structure.semantic.proposals import proposal_inputs


@cache
def release(custom_binding=False):
    core = Path(__file__).parents[2] / "src/corpus_structure/model/semantic/core.yaml"
    domain = b"""id: https://example.org/reasons
name: reasons
imports: [semantic_core]
prefixes: {ex: 'https://example.org/'}
default_prefix: ex
classes:
  Person:
    is_a: Entity
    attributes:
      name:
        range: ExpressionValue
        inlined: true
        annotations: {cs:role: predicate, cs:constraint_scope: accepted_value}
"""
    core_content = core.read_bytes()
    if custom_binding:
        import yaml

        schema = yaml.safe_load(core_content)
        schema["classes"]["DeclaredCustomBinding"] = {
            "is_a": "ExpressionBinding",
            "attributes": {"kind": {"equals_string": "custom_binding"}},
        }
        core_content = yaml.safe_dump(schema).encode()
    dependencies = domain_rule_inputs(ResolvedDependencies(), b"rules: []\n")
    bundle = proposal_inputs(
        SourceBundle(
            "reasons",
            (SourceArtifact("reasons", domain), SourceArtifact("semantic_core", core_content)),
        ),
        dependencies,
    )
    bundle, dependencies = analytical_inputs(bundle, dependencies)
    return prepare_release(
        bundle, composed_dependencies(dependencies), PreparationProfile(version="semantic-2")
    )
