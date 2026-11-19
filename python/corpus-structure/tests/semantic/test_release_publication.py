"""Pinned ontology membership retains its current schema and native archive meaning."""

import pytest
from pydantic import ValidationError
from sqlalchemy import select

from corpus_structure.semantic import releases
from corpus_structure.semantic.metadata import table
from corpus_structure.semantic.types import ResolvedDependencies, SourceArtifact
from semantic.releases_support import prepare_archive, source_bundle


def ontology_inputs():
    bundle = source_bundle()
    root, *imports = bundle.sources
    root = SourceArtifact(
        root.name,
        root.content.replace(
            b"classes:\n",
            b"enums:\n  Terms:\n    reachable_from: {source_ontology: terms, source_nodes: ['EX:1'], include_self: true}\nclasses:\n",
        ).replace(b"range: string", b"range: Terms\n        required: true"),
    )
    bundle = type(bundle)(bundle.root, (root, *imports))
    dependencies = ResolvedDependencies(
        artifacts=(
            SourceArtifact("terms", b"format-version: 1.2\n\n[Term]\nid: EX:1\nname: root\n"),
        ),
        ontology_sources=("terms",),
    )
    return prepare_archive(bundle, dependencies)


def test_current_schema_uses_exact_pinned_vocabulary_members():
    *_, prepared = ontology_inputs()
    assert prepared.enum_members("Terms") == {"EX:1"}
    assert prepared.validate_json("Child", b'{"id":"known","label":"EX:1"}').model_dump() == {
        "id": "known",
        "label": "EX:1",
    }
    with pytest.raises(ValidationError):
        prepared.validate_json("Child", b'{"id":"unknown","label":"EX:2"}')


def test_current_native_archive_preserves_pinned_ontology_membership(commit_db_engine):
    bundle, dependencies, profile, prepared = ontology_inputs()
    with commit_db_engine.begin() as connection:
        releases.persist_release(connection, bundle, dependencies, profile, prepared)
        members = table("sem.vocabulary_member")
        assert connection.execute(
            select(members.c.value).where(members.c.release_id == prepared.release_id)
        ).scalars().all() == ["EX:1"]
        loaded = releases.load_release(connection, prepared.release_id)
        assert loaded.enum_members("Terms") == {"EX:1"}
        with pytest.raises(ValidationError):
            loaded.validate_json("Child", b'{"id":"unknown","label":"EX:2"}')
