"""A runtime-only repair must not change the interpretation or identity of retained data."""

import json
from dataclasses import replace

import pytest

from corpus_structure.semantic.composed import composed_dependencies
from corpus_structure.semantic.contracts import (
    analysis_implementation_inputs,
    compile_execution_model,
    semantic_implementation_inputs,
    trusted_execution_inputs,
)
from corpus_structure.semantic.identity import canonical_bytes
from corpus_structure.semantic.prepare import prepare_release
from corpus_structure.semantic.runtime_bindings import (
    RuntimeBindingError,
    prepare_runtime_binding,
    require_installed_runtime,
    validate_runtime_binding,
)
from corpus_structure.semantic.types import PreparationProfile, ResolvedDependencies
from semantic.test_execution_release import _bundle


@pytest.fixture(scope="module")
def foundation():
    sources = analysis_implementation_inputs()
    execution = replace(
        trusted_execution_inputs(), implementations=semantic_implementation_inputs(sources)
    )
    bundle = _bundle()
    dependencies = composed_dependencies(ResolvedDependencies(), execution)
    profile = PreparationProfile(version="semantic-2")
    return (
        sources,
        execution,
        bundle,
        dependencies,
        profile,
        prepare_release(bundle, dependencies, profile),
    )


def test_exact_budget_repair_is_semantic_identity_neutral(foundation):
    sources, execution, bundle, dependencies, profile, prepared = foundation
    changed = []
    repaired = 0
    for source in sources:
        if source.name in {"invocation/operations.py", "package/semantic/operations.py"}:
            start = source.content.index(b"    def retained_source_result(")
            end = source.content.index(b"\n    def ", start + 1)
            method = source.content[start:end]
            assert method.count(b"read_budget=self._read_budget") == 2
            previous = method.replace(b"read_budget=self._read_budget", b"read_budget=budget")
            source = replace(
                source, content=source.content[:start] + previous + source.content[end:]
            )
            repaired += 1
        changed.append(source)
    assert repaired == 2  # Named consumer alias and exact package source are the same file.
    changed = tuple(changed)
    previous_execution = replace(execution, implementations=semantic_implementation_inputs(changed))
    assert compile_execution_model(previous_execution) == compile_execution_model(execution)
    previous_dependencies = composed_dependencies(ResolvedDependencies(), previous_execution)
    assert previous_dependencies == dependencies
    previous = prepare_release(bundle, previous_dependencies, profile)
    assert previous.release_id == prepared.release_id
    assert previous.manifest == prepared.manifest
    assert previous.definitions == prepared.definitions
    assert previous.registry_rows == prepared.registry_rows
    assert previous.artifacts == prepared.artifacts
    old_runtime = prepare_runtime_binding(previous, changed)
    current_runtime = prepare_runtime_binding(prepared, sources)
    assert old_runtime.release_id == current_runtime.release_id
    assert old_runtime.runtime_id != current_runtime.runtime_id
    validate_runtime_binding(old_runtime, prepared)
    with pytest.raises(RuntimeBindingError, match="installed runtime differs"):
        require_installed_runtime(prepared, old_runtime)


@pytest.mark.parametrize("name", ["grammar/extension.lark", "text/model.json"])
def test_parser_grammar_and_model_remain_semantic_determinants(foundation, name):
    _, execution, bundle, _, profile, prepared = foundation
    altered = []
    for source in execution.implementations:
        if source.name == name:
            if name.endswith(".lark"):
                content = source.content + b'\nadditional_scientific_symbol: "new_symbol"\n'
            else:
                model = json.loads(source.content)
                model[next(iter(model))] = "f" * 64
                content = canonical_bytes(model)
            source = replace(source, content=content)
        altered.append(source)
    candidate = replace(execution, implementations=tuple(altered))
    assert (
        compile_execution_model(candidate).model_id != compile_execution_model(execution).model_id
    )
    result = prepare_release(
        bundle, composed_dependencies(ResolvedDependencies(), candidate), profile
    )
    assert result.release_id != prepared.release_id


def test_data_schema_change_keeps_its_own_semantic_identity(foundation):
    _, _, bundle, dependencies, profile, prepared = foundation
    source = bundle.sources[0]
    assert b"      id:\n" in source.content
    changed = replace(
        source,
        content=source.content + b"      additional_meaning:\n        range: string\n",
    )
    result = prepare_release(replace(bundle, sources=(changed,)), dependencies, profile)
    assert result.release_id != prepared.release_id
    assert result.definitions != prepared.definitions


def test_runtime_archive_tampering_is_not_a_compatible_repair(foundation):
    sources, _, _, _, _, prepared = foundation
    binding = prepare_runtime_binding(prepared, sources)
    archive = json.loads(binding.archive)
    archive["inputs"][0]["content_hex"] += "00"
    with pytest.raises(RuntimeBindingError, match="digest differs"):
        validate_runtime_binding(replace(binding, archive=canonical_bytes(archive)), prepared)
