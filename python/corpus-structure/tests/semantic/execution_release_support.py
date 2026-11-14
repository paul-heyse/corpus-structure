"""Shared controlled inputs and builders for execution release support."""

from __future__ import annotations

from uuid import uuid4

from sqlalchemy import insert

from corpus_structure.semantic import (
    PreparationProfile,
    ResolvedDependencies,
    SourceArtifact,
    SourceBundle,
    prepare_release,
    releases,
)
from corpus_structure.semantic.composed import composed_dependencies
from corpus_structure.semantic.metadata import table


def bundle() -> SourceBundle:
    return SourceBundle(
        "domain",
        (
            SourceArtifact(
                "domain",
                b"""# Domain extraction remains a separate namespace.
id: https://example.org/execution-archive
name: domain
prefixes:
  ex: https://example.org/
default_prefix: ex
types:
  string:
    base: str
    uri: xsd:string
classes:
  Item:
    attributes:
      id:
        identifier: true
        range: string
""",
            ),
        ),
    )


def project(conn, release_id: str | None = None) -> str:
    project_id = str(uuid4())
    conn.execute(
        insert(table("data.project")).values(
            project_id=project_id, active_release_id=release_id, generation=0
        )
    )
    return project_id


def stage_authored_sql(conn):
    source = bundle()
    dependencies = composed_dependencies(
        ResolvedDependencies(
            (SourceArtifact("authored-sql/entities.sql", b"SELECT entity_id FROM data.entity"),)
        )
    )
    profile = PreparationProfile(version="semantic-2")
    prepared = prepare_release(source, dependencies, profile)
    releases.persist_release(conn, source, dependencies, profile, prepared)
    return prepared
