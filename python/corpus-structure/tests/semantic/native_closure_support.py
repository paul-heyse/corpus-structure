"""Shared controlled inputs and builders for native closure support."""

from __future__ import annotations

from corpus_structure.semantic import PreparationProfile, ResolvedDependencies, prepare_release
from corpus_structure.semantic.composed import composed_dependencies
from corpus_structure.semantic.releases import persist_release
from semantic.releases_support import source_bundle


def archive(engine):
    bundle = source_bundle()
    dependencies = composed_dependencies(ResolvedDependencies())
    profile = PreparationProfile(version="semantic-2")
    prepared = prepare_release(bundle, dependencies, profile)
    with engine.begin() as conn:
        persist_release(conn, bundle, dependencies, profile, prepared)
    return bundle, dependencies, profile, prepared
