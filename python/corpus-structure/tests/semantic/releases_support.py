"""Shared controlled inputs and builders for releases support."""

from __future__ import annotations

from corpus_structure.semantic import (
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


def prepare_archive(bundle=None, dependencies=ResolvedDependencies()):
    from dataclasses import replace
    import yaml

    from semantic.data_operation_kernel_support import STORAGE, prepare_kernel

    captured = prepare_kernel(STORAGE)
    schema = yaml.safe_load(captured.bundle.sources[0].content)
    del schema["types"]["string"]  # the archive's imported base declares the same XSD type
    source = SourceArtifact("target", yaml.safe_dump(schema).encode())
    bundle = source_bundle() if bundle is None else bundle
    # The native archive requires the actual complete current operation projection.
    # Keep the independent archive schema bytes and order, composing the controlled
    # STORAGE producer schema as an explicit import rather than fabricating authority.
    bundle = replace(
        bundle,
        sources=(
            replace(
                bundle.sources[0],
                content=bundle.sources[0].content.replace(
                    b"imports: [base]", b"imports: [base, target]"
                ),
            ),
            *bundle.sources[1:],
            source,
        ),
    )
    dependencies = ResolvedDependencies(
        artifacts=(*captured.dependencies.artifacts, SourceArtifact("opaque", b"\x00exact external bytes\xff"), *dependencies.artifacts),
        vocabularies=dependencies.vocabularies,
        ontology_sources=dependencies.ontology_sources,
    )
    profile = captured.profile
    prepared = prepare_release(bundle, dependencies, profile)
    return bundle, dependencies, profile, prepared


def stage(conn, bundle=None):
    bundle, dependencies, profile, prepared = prepare_archive(bundle)
    releases.persist_release(conn, bundle, dependencies, profile, prepared)
    return bundle, dependencies, profile, prepared
