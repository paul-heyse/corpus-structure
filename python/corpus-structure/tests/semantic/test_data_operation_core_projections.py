"""One captured Core projection supplies native SQL and decoder row shape."""
import json

import pglast

from corpus_structure.semantic.data_operation_projections import binding_columns, capture_projection_sources, member_columns
from corpus_structure.semantic.data_operation_storage import native_protocol_sources, native_sql


def test_captured_core_products_own_return_shape_and_keep_scoped_native_parameters():
    sources = {source.name: source.content for source in capture_projection_sources()}
    products = json.loads(sources["native/data-operation-projections.json"])
    assert {column.name for column in binding_columns()} == {column.name for column in binding_columns(decoder=True)}
    assert "provider_identity" in member_columns()
    assert '"analyzed_scope" JSONB' in products["binding_returns"]
    for name in ("support_scopes", "binding_computed", "binding_original", "read_page"):
        assert pglast.parse_sql(products[name])
    assert "support_closure" in products["support_scopes"]
    assert "data_derivation_original_support" in products["support_scopes"]
    assert "p_operation" in products["binding_computed"]
    assert "after_key" in products["read_page"] and "LIMIT lim" in products["read_page"]
    assert "ops.ddo_episode_provider_identity" in products["binding_computed"]


def test_native_sql_uses_frozen_core_products_without_ambient_builder(monkeypatch):
    captured = native_protocol_sources()
    first = native_sql(captured)
    import corpus_structure.semantic.data_operation_projections as projections
    monkeypatch.setattr(projections, "capture_projection_sources", lambda: (_ for _ in ()).throw(AssertionError("ambient builder")))
    assert native_sql(captured) == first
    assert "__DDO_CORE_" not in first
    assert pglast.parse_sql(first)
