"""Named-query custody, with independent rows and deliberate implementation edits."""

import base64
import importlib.util
import json
import sys
from dataclasses import replace
from pathlib import Path

import pytest

from corpus_structure.semantic import ResolvedDependencies, prepare_release
from corpus_structure.semantic.continuations import decode_continuation
from corpus_structure.semantic.query_compatibility import (
    QueryCompatibilityError,
    acquire_query_inputs,
    open_query_registry,
    prepare_query_bindings,
)

from .test_releases import source_bundle

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
    registry = open_query_registry(prepared, pack, query_name="claims")
    claims = registry["claims"]
    assert claims.release_id == prepared.release_id
    assert claims.implementation == claims.producing_implementation
    assert claims.version == "ordinary-answer-2"
    assert any(artifact.kind == "query_bindings.json" for artifact in prepared.artifacts)


def test_preimported_exact_object_lowering_is_captured_and_edits_refuse(tmp_path, monkeypatch):
    from corpus_structure.semantic.consolidation import plain

    pack, release, inputs = prepared_pack(tmp_path)
    name = "operation/query-source/runtime/semantic/consolidation.py"
    captured = next(item for item in inputs if item.name == name)
    filename = sys.modules[plain.__module__].__file__
    assert filename is not None
    path = Path(filename)
    assert captured.content == path.read_bytes()
    assert open_query_registry(release, pack, query_name="probe")["probe"].name == "probe"
    original = Path.read_bytes

    def edited(self):
        content = original(self)
        return content + b"\n# changed exact-object lowering\n" if self == path else content

    monkeypatch.setattr(Path, "read_bytes", edited)
    with pytest.raises(QueryCompatibilityError, match="restart"):
        acquire_query_inputs(pack)


def compatibility(pack, query, *, duplicate=False):
    entry = dict(
        query="probe",
        contract=query.contract,
        implementation=query.producing_implementation,
        evidence="independent probe rows 1,2,3",
    )
    declaration = pack / "query-bundle.json"
    body = json.loads(declaration.read_text()) if declaration.is_file() else {}
    body["compatibility"] = [entry] * (2 if duplicate else 1)
    declaration.write_text(json.dumps(body))


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
    query = open_query_registry(prepared, pack, query_name="probe")["probe"]
    assert [v.row.value for v in query.rows(None, query.params(minimum=2))] == [2, 3]
    assert query.release_id == prepared.release_id


def test_same_version_edit_refuses_before_plugin_import(tmp_path):
    pack, prepared, _ = prepared_pack(tmp_path)
    (pack / "queries.py").write_text("raise AssertionError('changed code was imported')\n" + PLUGIN)
    with pytest.raises(QueryCompatibilityError) as caught:
        open_query_registry(prepared, pack, query_name="probe")
    assert caught.value.reason == "incompatible_query"


def test_explicit_compatible_source_change_keeps_producing_contract(tmp_path):
    pack, prepared, _ = prepared_pack(tmp_path)
    original = open_query_registry(prepared, pack, query_name="probe")["probe"]
    (pack / "queries.py").write_text(
        "# same behavior, new source custody\n" + PLUGIN.replace("'probe', '1'", "'probe', '2'")
    )
    with pytest.raises(QueryCompatibilityError):
        open_query_registry(prepared, pack, query_name="probe")
    compatibility(pack, original)
    supported = open_query_registry(prepared, pack, query_name="probe")["probe"]
    assert [v.row.value for v in supported.rows(None, supported.params())] == [1, 2, 3]
    assert supported.contract == original.contract and supported.version == "1"
    assert supported.implementation != original.implementation
    assert supported.producing_implementation == original.implementation


def test_ambiguous_compatibility_and_changed_shape_refuse(tmp_path):
    pack, prepared, _ = prepared_pack(tmp_path)
    original = open_query_registry(prepared, pack, query_name="probe")["probe"]
    compatibility(pack, original, duplicate=True)
    with pytest.raises(QueryCompatibilityError, match="ambiguous"):
        open_query_registry(prepared, pack, query_name="probe")
    compatibility(pack, original)
    (pack / "queries.py").write_text(PLUGIN.replace("value: int", "value: str"))
    with pytest.raises(QueryCompatibilityError, match="contract differs"):
        open_query_registry(prepared, pack, query_name="probe")


def test_missing_binding_and_old_token_reader_refuse(tmp_path):
    pack, _, _ = prepared_pack(tmp_path)
    with pytest.raises(QueryCompatibilityError) as caught:
        open_query_registry(prepare_release(source_bundle()), pack)
    assert caught.value.reason == "unavailable_query"
    token = base64.urlsafe_b64encode(b'{"run":1}').decode()
    with pytest.raises(QueryCompatibilityError) as caught:
        decode_continuation(token, kind="named")
    assert caught.value.reason == "unsupported_query_token"


def test_qualified_import_failure_remains_programming_failure(tmp_path):
    pack, prepared, _ = prepared_pack(tmp_path)
    original = open_query_registry(prepared, pack, query_name="probe")["probe"]
    compatibility(pack, original)
    (pack / "queries.py").write_text("raise RuntimeError('implementation failure')\n" + PLUGIN)
    with pytest.raises(RuntimeError, match="implementation failure"):
        open_query_registry(prepared, pack, query_name="probe")


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
        prepared = prepare_release(source_bundle(), ResolvedDependencies(inputs))
        original = open_query_registry(prepared, pack, query_name="probe")["probe"]
        helper.write_text("VALUE = 2\n")
        if remove_module:
            sys.modules.pop(name)
        compatibility(pack, original)
        with pytest.raises(QueryCompatibilityError, match="restart"):
            open_query_registry(prepared, pack, query_name="probe")
    finally:
        sys.modules.pop(name, None)


@pytest.mark.parametrize("invalid", [False, True])
def test_query_result_admission_preserves_concrete_nested_qualification(
    tmp_path,
    monkeypatch,
    invalid,
):
    from types import SimpleNamespace
    from unittest.mock import Mock

    from pydantic import ValidationError
    from sqlalchemy import Connection

    from corpus_structure.semantic.query import CoverageSummary, SnapshotBinding
    from corpus_structure.serve import journey

    pack = tmp_path / "qualified"
    pack.mkdir()
    source = """from decimal import Decimal
from pydantic import BaseModel, SerializeAsAny
from corpus_structure.serve.protocol import Positioned, Scope
class Params(BaseModel):
    pass
class Qualification(BaseModel):
    amount: Decimal
class Row(BaseModel):
    qualification: SerializeAsAny[BaseModel]
class Query:
    name, version, params, result = 'qualified', '1', Params, Row
    def scope(self, ctx, p): return Scope.run()
    def rows(self, ctx, p, after=None):
        yield Positioned(Row(qualification=Qualification(amount=Decimal('1.2300'))), 1)
QUERIES=[Query()]
"""
    if invalid:
        source = source.replace(
            "Row(qualification=Qualification(amount=Decimal('1.2300')))",
            "Row.model_construct(qualification=1)",
        )
    (pack / "queries.py").write_text(source)
    inputs = acquire_query_inputs(pack)
    prepared = prepare_release(source_bundle(), ResolvedDependencies(inputs))
    registry = open_query_registry(prepared, pack)
    binding = SnapshotBinding(prepared.release_id, "result", 0, "capture")
    monkeypatch.setattr(journey, "check_finished", lambda conn, run: run)
    monkeypatch.setattr(
        journey,
        "bind_session",
        lambda conn, run: SimpleNamespace(
            binding=binding,
            completed_cut_id=7,
            coverage_summary=lambda requirement: CoverageSummary(state="not_established"),
        ),
    )
    if invalid:
        with pytest.raises(ValidationError, match="qualification"):
            journey.serve_query(Mock(spec=Connection), registry, "qualified", run=1)
        return
    page = journey.serve_query(Mock(spec=Connection), registry, "qualified", run=1)
    assert page.rows == [{"qualification": {"amount": "1.2300"}}]
