"""One captured Core projection supplies native SQL and decoder row shape."""

import json

import pglast
import pytest

from corpus_structure.semantic.data_operation_projections import (
    binding_columns,
    capture_projection_sources,
    member_columns,
)
from corpus_structure.semantic.data_operation_storage import native_protocol_sources, native_sql


def test_captured_core_products_own_return_shape_and_keep_scoped_native_parameters():
    sources = {source.name: source.content for source in capture_projection_sources()}
    products = json.loads(sources["native/data-operation-projections.json"])
    assert {column.name for column in binding_columns()} == {
        column.name for column in binding_columns(decoder=True)
    }
    assert "provider_identity" in member_columns()
    assert '"analyzed_scope" JSONB' in products["binding_returns"]
    for name in (
        "read_scope_rows",
        "cancellation_scopes",
        "binding_computed",
        "binding_original",
        "read_page",
    ):
        assert pglast.parse_sql(products[name])
    assert "support_closure" in products["read_scope_rows"]
    assert "data_derivation_original_support" in products["read_scope_rows"]
    assert "p_operation" in products["binding_computed"]
    assert "after_key" in products["read_page"] and "LIMIT lim" in products["read_page"]
    assert "ops.ddo_episode_provider_identity" in products["binding_computed"]


def test_native_sql_uses_frozen_core_products_without_ambient_builder(monkeypatch):
    captured = native_protocol_sources()
    first = native_sql(captured)
    import corpus_structure.semantic.data_operation_projections as projections

    monkeypatch.setattr(
        projections,
        "capture_projection_sources",
        lambda: (_ for _ in ()).throw(AssertionError("ambient builder")),
    )
    assert native_sql(captured) == first
    assert "__DDO_CORE_" not in first
    assert pglast.parse_sql(first)


def test_captured_sql_scope_projection_follows_its_domain_function_providers():
    from pglast import ast
    from pglast.visitors import Visitor

    from corpus_structure.semantic.native_sql_body import body_source
    from corpus_structure.semantic.prepared_sql import prepare_sql

    captured = native_protocol_sources()
    scope_source = next(source for source in captured
                        if source.name == "native/data-operation-support-scopes.sql")
    assert "CREATE OR REPLACE FUNCTION ops.ddo_support_scopes" in scope_source.content.decode()
    prepared = prepare_sql(native_sql(captured), source="scope-provider-installation-order")
    declarations = {
        tuple(part.sval for part in statement.stmt.funcname): (index, statement.stmt)
        for index, statement in enumerate(prepared.statements)
        if isinstance(statement.stmt, ast.CreateFunctionStmt)
    }
    index, scope = declarations[("ops", "ddo_support_scopes")]
    assert next(option.arg.sval for option in scope.options if option.defname == "language") == "sql"
    calls = set()

    class Calls(Visitor):
        def visit_FuncCall(self, ancestors, node):
            calls.add(tuple(part.sval for part in node.funcname))

    Calls()(prepare_sql(body_source(scope), source="captured-scope-body").private_tree())
    providers = {
        ("ops", "ddo_record_grade_dependency_scopes"),
        ("ops", "ddo_record_fit_dependency_scopes"),
        ("ops", "ddo_operation_event_dependency_scopes"),
    }
    # These are the actual captured body calls, not a source-order smoke test.
    assert providers <= calls
    assert all(declarations[provider][0] < index for provider in providers)
    assert declarations[("ops", "ddo_scope")][0] < index



def test_core_projection_capture_consumes_explicit_counterfactual_metadata_without_ambient_fallback(
    monkeypatch,
):
    import pytest
    import yaml

    import corpus_structure.schema.physical as physical
    from corpus_structure.semantic.metadata import metadata

    sources = dict(metadata.info["physical_sources"])
    types = metadata.info["physical_linkml_types"]
    document = yaml.safe_load(sources["data-operation-physical.yaml"])
    document["classes"]["data_obligation"]["attributes"]["counterfactual_marker"] = {
        "range": "string"
    }
    sources["data-operation-physical.yaml"] = yaml.safe_dump(document).encode()
    proposed = physical.compile_physical(sources, linkml_types=types)
    assert "counterfactual_marker" in proposed.tables["ops.data_obligation"].c

    def unavailable(*args, **kwargs):
        raise AssertionError("ambient physical acquisition")

    monkeypatch.setattr(physical, "physical_source_closure", unavailable)
    monkeypatch.setattr(physical, "linkml_types_source", unavailable)
    captured = capture_projection_sources(
        physical_sources=proposed.info["physical_sources"],
        linkml_types=proposed.info["physical_linkml_types"],
    )
    products = json.loads(
        next(
            source.content
            for source in captured
            if source.name == "native/data-operation-projections.json"
        )
    )
    assert "data_obligation.counterfactual_marker" in products["read_page"]
    assert (
        next(
            source.content
            for source in captured
            if source.name == "native/projection-physical/data-operation-physical.yaml"
        )
        == sources["data-operation-physical.yaml"]
    )
    with pytest.raises(ValueError, match="captured LinkML types"):
        capture_projection_sources(physical_sources=sources)
    with pytest.raises(ValueError, match="physical closure"):
        capture_projection_sources(physical_sources={}, linkml_types=types)


@pytest.mark.parametrize("change", ["retire", "rename", "reclassify"])
def test_intrinsic_trigger_inventory_follows_captured_target_classes_without_ambient_fallback(
    change, monkeypatch, tmp_path
):
    import yaml

    from corpus_structure.schema.physical import compile_physical
    from corpus_structure.semantic import data_operation_storage as storage
    from corpus_structure.semantic.metadata import metadata

    sources = dict(metadata.info["physical_sources"])
    declaration = yaml.safe_load(sources["data-operation-physical.yaml"])
    name = "data_attempt_failure"
    if change == "retire":
        declaration["classes"].pop(name)
    elif change == "rename":
        declaration["classes"]["renamed_attempt_failure"] = declaration["classes"].pop(name)
    else:
        declaration["classes"][name]["annotations"]["ph:immutability"] = "physical"
    sources["data-operation-physical.yaml"] = yaml.safe_dump(declaration).encode()
    proposed = compile_physical(sources, linkml_types=metadata.info["physical_linkml_types"])
    # This table has no incoming foreign keys; each proposed physical declaration
    # remains coherent independently of the fixed current read function's support.
    assert proposed.sorted_tables
    monkeypatch.setattr(storage, "_ROOT", tmp_path / "unavailable-installed-model")
    names = {
        relation.fullname
        for relation in storage.data_operation_immutable_relations(proposed, sources)
    }
    assert "ops.data_attempt_failure" not in names
    assert "ops.data_derivation" in names
    assert ("ops.renamed_attempt_failure" in names) is (change == "rename")
    # Retaining a captured intrinsic declaration while changing only mutable
    # metadata cannot silently reclassify it or borrow the installed table.
    if change == "rename":
        proposed.tables["ops.renamed_attempt_failure"].info["immutability"] = "physical"
        with pytest.raises(ValueError, match="differs from captured class"):
            storage.data_operation_immutable_relations(proposed, sources)
