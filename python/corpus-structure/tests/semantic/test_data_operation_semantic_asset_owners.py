"""Actual family source custody, semantic prose locality and opaque algorithm changes."""

import json
from pathlib import Path

from corpus_structure.semantic.data_operation_compilation import compile_data_operations
from corpus_structure.semantic.finite_interpretation_products import (
    finite_interpretation_assets,
    finite_interpretation_inputs,
    finite_interpretation_operation_sources,
)
from corpus_structure.semantic.types import SourceArtifact, SourceBundle


class OverlayRoot:
    def __init__(self, root, overrides):
        self.root, self.overrides = root, overrides

    def __truediv__(self, name):
        return self.overrides.get(name, self.root / name)


def recipe(model):
    return next(identity.key for identity in model.identities if identity.domain == "recipe")


def test_actual_finite_wrapper_prose_is_custody_but_algorithm_remains_semantic(monkeypatch, tmp_path):
    from corpus_structure.semantic import finite_interpretation_products as owner

    root = Path(__file__).parents[2] / "src/corpus_structure"
    bundle = finite_interpretation_inputs(SourceBundle("core", (SourceArtifact("core", (root / "model/semantic/core.yaml").read_bytes()),)))
    before_sources = finite_interpretation_operation_sources()
    before_asset = finite_interpretation_assets()
    before = compile_data_operations(bundle, python_sources=before_sources)
    wrapper = "methods/finite_interpretation.py"
    files = dict(json.loads(before_asset.content)["files"])
    assert json.loads(bytes.fromhex(files[wrapper]))["interpretation"] == "admitted-operation-module-v1"
    assert "semantic/record_interpretation.py" in files
    wrapper_bytes = (root / wrapper).read_bytes()
    changed = wrapper_bytes.replace(
        b'"behavior": "', b'"behavior": "Reworded description. '
    ).replace(b"retained-private-candidates-and-explicit-policy", b"Descriptive applicability reworded")
    assert changed != wrapper_bytes
    altered_wrapper = tmp_path / "finite_interpretation.py"
    altered_wrapper.write_bytes(changed)
    monkeypatch.setattr(owner, "_ROOT", OverlayRoot(root, {wrapper: altered_wrapper}))
    after_sources = finite_interpretation_operation_sources()
    after = compile_data_operations(bundle, python_sources=after_sources)
    assert finite_interpretation_assets().content == before_asset.content
    assert before_sources.sources[0].content != after_sources.sources[0].content
    assert before.content != after.content
    assert before.operations[0].capabilities.prepared_factory is not None
    assert after.operations[0].capabilities.prepared_factory is not None
    assert before.operations[0].capabilities.prepared_factory.source_digest != after.operations[0].capabilities.prepared_factory.source_digest
    assert before.operations[0].capabilities.prepared_factory.semantic_digest == after.operations[0].capabilities.prepared_factory.semantic_digest
    assert before.operations[0].definition == after.operations[0].definition
    assert recipe(before) == recipe(after)

    # The wrapper's executable body remains owned by its admitted slice.
    altered_wrapper.write_bytes(changed.replace(
        b"return execute_finite_profile(self, candidates, policy)",
        b"return execute_finite_profile(self, candidates, {**policy, 'mode': 'constraints'})",
    ))
    executable = compile_data_operations(bundle, python_sources=finite_interpretation_operation_sources())
    assert recipe(executable) != recipe(before)

    # A factory can change behavior even when the operation's run slice is unchanged.
    factory = changed.replace(b"return resolve_finite_port(", b"raise ValueError('changed acquisition behavior')\n        return resolve_finite_port(")
    assert factory != changed
    altered_wrapper.write_bytes(factory)
    factory_model = compile_data_operations(bundle, python_sources=finite_interpretation_operation_sources())
    assert factory_model.operations[0].capabilities.prepared_factory is not None
    assert factory_model.operations[0].capabilities.prepared_factory.semantic_digest != before.operations[0].capabilities.prepared_factory.semantic_digest
    assert recipe(factory_model) != recipe(before)
    # Complete supplying-module globals remain captured, including factory dependencies.
    from corpus_structure.semantic.python_module_projection import admitted_operation_module_digest
    first_global = b"FACTORY_POLICY = 1\n" + factory
    second_global = first_global.replace(b"FACTORY_POLICY = 1", b"FACTORY_POLICY = 2")
    assert admitted_operation_module_digest(first_global) != admitted_operation_module_digest(second_global)

    # A genuinely opaque array algorithm retains exact source-byte responsibility.
    algorithm = "semantic/record_interpretation.py"
    altered_algorithm = tmp_path / "record_interpretation.py"
    original_algorithm = (root / algorithm).read_bytes()
    altered_algorithm.write_bytes(original_algorithm.replace(b"np.float64", b"np.float32"))
    assert altered_algorithm.read_bytes() != original_algorithm
    monkeypatch.setattr(owner, "_ROOT", OverlayRoot(root, {algorithm: altered_algorithm}))
    assert finite_interpretation_assets().digest != before_asset.digest
    algorithm_model = compile_data_operations(bundle, python_sources=finite_interpretation_operation_sources())
    assert recipe(algorithm_model) != recipe(before)


def test_module_projection_retains_executable_locals_and_ordinary_class_attributes():
    from corpus_structure.semantic.python_module_projection import admitted_operation_module_digest

    local = b"def run():\n    __data_operation__ = {'value': 1}\n    return __data_operation__['value']\n"
    assert admitted_operation_module_digest(local) != admitted_operation_module_digest(local.replace(b"'value': 1", b"'value': 2"))
    attribute = b"class Data:\n    ordinary__data_operation__ = {'value': 1}\n"
    assert admitted_operation_module_digest(attribute) != admitted_operation_module_digest(attribute.replace(b"'value': 1", b"'value': 2"))
