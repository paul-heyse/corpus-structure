"""Retained pack-query acquisition and pure compilation preserve exact source custody."""

import importlib.util
import json
import sys
from dataclasses import replace
from pathlib import Path
from unittest.mock import Mock

import pytest
from sqlalchemy import Connection

from corpus_structure.semantic import ResolvedDependencies, prepare_release
from corpus_structure.semantic.query_compatibility import (
    QueryCompatibilityError,
    _registry,
    acquire_query_inputs,
    installed_query_inputs,
    prepare_query_bindings,
)
from corpus_structure.serve.protocol import QueryContext
from semantic.releases_support import source_bundle

PLUGIN = """from pydantic import BaseModel
from corpus_structure.serve.protocol import Positioned, Scope
class Params(BaseModel):
    minimum: int = 1
class Row(BaseModel):
    value: int
class Query:
    name, version, params, result = 'probe', '1', Params, Row
    def scope(self, ctx, p): return Scope.run()
    def rows(self, ctx, p, after=None):
        for i in (1,2,3):
            if i >= p.minimum and (after is None or i > after):
                yield Positioned(Row(value=i), i)
QUERIES=[Query()]
"""


def prepared_pack(tmp_path):
    pack = tmp_path / "statistics"
    pack.mkdir()
    (pack / "queries.py").write_text(PLUGIN)
    inputs = acquire_query_inputs(pack)
    prepared = prepare_release(source_bundle(), ResolvedDependencies(inputs))
    return pack, prepared, inputs


def test_actual_statistics_pack_acquisition_binds_installed_queries():
    from corpus_structure.semantic.regeneration import prepare_pack

    pack = Path(__file__).resolve().parents[4] / "domains/statistics"
    _, dependencies, _, prepared = prepare_pack(pack)
    assert any(
        source.name.endswith("operation/query-manifest.json") for source in dependencies.artifacts
    )
    artifact = next(a for a in prepared.artifacts if a.kind == "query_bindings.json")
    claims = next(
        row
        for row in json.loads(artifact.content)["bindings"]
        if row["pack"] == "statistics" and row["query"]["name"] == "claims"
    )
    assert claims["query"]["version"] == "ordinary-answer-2"
    assert claims["query"]["required_operations"] == ["query"]


def test_preimported_exact_object_lowering_is_captured_and_edits_refuse(tmp_path, monkeypatch):
    from corpus_structure.semantic.consolidation import plain

    pack, _, inputs = prepared_pack(tmp_path)
    name = "operation/query-source/runtime/semantic/consolidation.py"
    captured = next(item for item in inputs if item.name == name)
    filename = sys.modules[plain.__module__].__file__
    assert filename is not None
    path = Path(filename)
    assert captured.content == path.read_bytes()
    assert _registry(installed_query_inputs(pack))["probe"].name == "probe"
    original = Path.read_bytes

    def edited(self):
        content = original(self)
        return content + b"\n# changed exact-object lowering\n" if self == path else content

    monkeypatch.setattr(Path, "read_bytes", edited)
    with pytest.raises(QueryCompatibilityError, match="restart"):
        acquire_query_inputs(pack)


def test_exact_bundle_derived_product_and_independent_rows(tmp_path, monkeypatch):
    pack, prepared, inputs = prepared_pack(tmp_path)
    from corpus_structure.semantic import query_compatibility as owner

    def refuse_io(*args):
        raise AssertionError("pure preparation must use supplied bytes")

    monkeypatch.setattr(owner, "installed_query_inputs", refuse_io)
    products = prepare_query_bindings(ResolvedDependencies(inputs))
    assert products is not None
    artifact, rows = products
    assert artifact == next(a for a in prepared.artifacts if a.kind == "query_bindings.json")
    assert any(row.name == "statistics/probe" for row in rows)
    monkeypatch.undo()
    query = _registry(installed_query_inputs(pack))["probe"]
    assert [
        v.row.model_dump()["value"]
        for v in query.rows(QueryContext(1, Mock(spec=Connection)), query.params(minimum=2))
    ] == [2, 3]


def test_qualified_import_failure_remains_programming_failure(tmp_path):
    pack, _, _ = prepared_pack(tmp_path)
    (pack / "queries.py").write_text("raise RuntimeError('implementation failure')\n" + PLUGIN)
    with pytest.raises(RuntimeError, match="implementation failure"):
        acquire_query_inputs(pack)


def test_source_custody_and_loaded_helper_lifetime_refuse(tmp_path, monkeypatch):
    _pack, _, inputs = prepared_pack(tmp_path)
    corrupt = (*inputs[:-1], replace(inputs[-1], content=b"changed source bytes"))
    with pytest.raises(QueryCompatibilityError, match="source custody"):
        prepare_query_bindings(ResolvedDependencies(corrupt))
    warm = tmp_path / "warm"
    warm.mkdir()
    (warm / "queries.py").write_text(PLUGIN)
    helper = warm / "helper.py"
    helper.write_text("VALUE = 1\n")
    (warm / "query-bundle.json").write_text(json.dumps({"sources": ["helper.py"]}))
    spec = importlib.util.spec_from_file_location("before_query_acquisition", helper)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    monkeypatch.setitem(sys.modules, spec.name, module)
    spec.loader.exec_module(module)
    assert module.VALUE == 1
    helper.write_text("VALUE = 2\n")
    # No first registry observation is being mistaken for source-load custody:
    # this helper was imported before the first acquisition of this bundle.
    with pytest.raises(QueryCompatibilityError, match="restart"):
        acquire_query_inputs(warm)


@pytest.mark.parametrize("remove_module", [False, True])
def test_declared_helper_normal_import_has_exact_custody_then_refuses_edit(
    tmp_path,
    monkeypatch,
    remove_module,
):
    pack = tmp_path / "helpers"
    pack.mkdir()
    name = "owned_query_helper"
    helper = pack / (name + ".py")
    helper.write_text("VALUE = 1\n")
    (pack / "queries.py").write_text("import " + name + "\n" + PLUGIN)
    (pack / "query-bundle.json").write_text(json.dumps({"sources": [helper.name]}))
    monkeypatch.syspath_prepend(str(pack))
    try:
        inputs = acquire_query_inputs(pack)
        assert sys.modules[name].VALUE == 1
        assert prepare_query_bindings(ResolvedDependencies(inputs)) is not None
        helper.write_text("VALUE = 2\n")
        if remove_module:
            sys.modules.pop(name)
        with pytest.raises(QueryCompatibilityError, match="restart"):
            acquire_query_inputs(pack)
    finally:
        sys.modules.pop(name, None)
