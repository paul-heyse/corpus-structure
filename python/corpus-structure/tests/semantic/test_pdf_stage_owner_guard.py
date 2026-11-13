"""Actual source-authored PDF guard checked without changing frozen admission."""

from corpus_structure.semantic.native_candidate import _pdf_payload_definitions
from corpus_structure.semantic.native_objects import (
    NativeIdentity,
    observe_native,
    prepare_native_authoring,
)
from corpus_structure.semantic.pdf_staging_native import stage_native_sql

def test_current_pdf_stage_owner_static_check_preserves_frozen_kernel(semantic_db_engine):
    identity = NativeIdentity("function", "ops", "require_pdf_stage_owner", ("bigint", "bigint", "text"))
    with semantic_db_engine.begin() as connection:
        before = observe_native(connection, identity, catalog_version=1)
        selected = next(
            item for item in _pdf_payload_definitions(
                connection, stage_native_sql(), source="current PDF owner guard", current_source=True,
            ) if item.identity == identity
        )
        # The authoring checker traverses both the legacy and request-backed branches
        # against the real installed row types and native dependencies.
        prepared = prepare_native_authoring(
            connection, (selected,), owned_authoring=True, check_plpgsql=frozenset({identity}),
        )
        assert prepared.desired[0].identity == identity
        assert prepared.desired[0].catalog["owner"] == "corpus_sem_publisher"
        assert prepared.desired[0].catalog["security"] is True
        assert observe_native(connection, identity, catalog_version=1) == before
