"""Shared controlled inputs and builders for releases support."""

from __future__ import annotations

from corpus_structure.semantic import (
    PreparationProfile,
    ResolvedDependencies,
    SourceArtifact,
    SourceBundle,
    prepare_release,
    releases,
)


def source_bundle(extra: bytes = b"") -> SourceBundle:
    # Deliberately preserve comments, CRLF and source/dependency ordering independently
    # of YAML's interpreted meaning and the compiler's sorted digest manifest.
    return SourceBundle(
        "archive",
        (
            SourceArtifact(
                "archive",
                b"""id: https://example.org/archive
name: archive
prefixes:
  ex: https://example.org/
default_prefix: ex
imports: [base]
classes:
  Child:
    is_a: Parent
    attributes:
      label:
        range: string
"""
                + extra,
            ),
            SourceArtifact(
                "base",
                b"""# exact imported bytes
id: https://example.org/base
name: base
prefixes:
  ex: https://example.org/
default_prefix: ex
types:
  string:
    base: str
    uri: xsd:string
classes:
  Parent:
    attributes:
      id:
        identifier: true
""".replace(b"\n", b"\r\n"),
            ),
        ),
    )


def stage(conn, bundle=None, *, composed=True):
    bundle = source_bundle() if bundle is None else bundle
    dependencies = ResolvedDependencies(
        (SourceArtifact("opaque", b"\x00exact external bytes\xff"),)
    )
    from corpus_structure.semantic.composed import composed_dependencies

    if composed:
        dependencies = composed_dependencies(dependencies)
    profile = PreparationProfile(version="semantic-2" if composed else "semantic-1")
    prepared = prepare_release(bundle, dependencies, profile)
    releases.persist_release(conn, bundle, dependencies, profile, prepared)
    return bundle, dependencies, profile, prepared
