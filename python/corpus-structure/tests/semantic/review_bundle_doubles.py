"""Disables source projection verification for hand-authored bundles; the real native check is covered by semantic.test_condition_publication_native.test_condition_admits_only_the_exact_supported_roles."""

import pytest


@pytest.fixture
def synthetic_source_projection(monkeypatch):
    # These controls use hand-written structural scopes and opaque product IDs.
    # The native fold and its mandatory bundle boundary are exercised separately.
    from corpus_structure.serve import review_bundle

    monkeypatch.setattr(review_bundle, "_verify_source_projections", lambda *_: set())
