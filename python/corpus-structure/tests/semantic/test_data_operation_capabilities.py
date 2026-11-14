"""Captured capabilities and terminal settlement retain independent meaning."""

import copy
import importlib
import json
from dataclasses import replace
from hashlib import sha256

import pytest

from corpus_structure.semantic.data_operation_compilation import compile_data_operations
from corpus_structure.semantic.data_operation_consumers import resolve_prepared_factory
from corpus_structure.semantic.data_operation_model import (
    MODEL_VERSION,
    PREVIOUS_MODEL_VERSION,
    read_effective_data_operations,
)
from corpus_structure.semantic.identity import claim_source_item__data_operation__
from corpus_structure.semantic.python_operation_sources import PythonSource, PythonSourceCollection


def test_compiled_factory_is_captured_from_original_static_owner(tmp_path, monkeypatch):
    metadata = copy.deepcopy(claim_source_item__data_operation__)
    metadata['entrypoints'] = ['run']
    metadata['capabilities']['prepared_factory'] = 'acquire_port'
    name = 'captured_factory_' + tmp_path.name.replace('-', '_')
    source = ('class Operation:\n'
              '    def run(self, index: int) -> str: return str(index)\n'
              '    @staticmethod\n'
              '    def acquire_port(*args, **kwargs): return "captured"\n'
              f'Operation.__data_operation__ = {metadata!r}\n')
    path = tmp_path / (name + '.py')
    path.write_text(source)
    monkeypatch.syspath_prepend(str(tmp_path))
    sources = PythonSourceCollection((PythonSource(name, source.encode(), str(path)),))
    model = compile_data_operations(python_sources=sources)
    operation = model.operations[0]
    assert model.version == MODEL_VERSION
    assert operation.capabilities.prepared_factory.entrypoint == name + '.Operation.acquire_port'
    assert operation.capabilities.prepared_factory.source_digest == sha256(source.encode()).hexdigest()
    acquired = resolve_prepared_factory(model, sources, operation.semantic_id)
    assert acquired() == 'captured'
    monkeypatch.setattr(importlib.import_module(name).Operation, 'acquire_port', staticmethod(lambda: 'changed'))
    with pytest.raises(ValueError, match='rebound'):
        acquired()


def test_exact_v3_archive_read_has_no_current_execution_authority():
    model = compile_data_operations()
    previous = replace(model, version=PREVIOUS_MODEL_VERSION)
    content = previous.content
    reopened = read_effective_data_operations(content)
    assert reopened.content == content
    assert json.loads(content)['version'] == PREVIOUS_MODEL_VERSION
    with pytest.raises(ValueError, match='historical'):
        reopened.projection_graph('semantic-reference')
