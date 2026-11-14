"""Shared controlled inputs and builders for operation reporting support."""

from functools import lru_cache

from corpus_structure.semantic.composed import composed_dependencies
from corpus_structure.semantic.prepare import prepare_release
from corpus_structure.semantic.types import (
    PreparationProfile,
    ResolvedDependencies,
    SourceArtifact,
    SourceBundle,
)


@lru_cache(maxsize=1)
def report_inputs():
    source = SourceArtifact(
        "m",
        b"""id: https://example.org/report-test
name: report_test
prefixes: {ex: 'https://example.org/'}
default_prefix: ex
types:
 string: {base: str, uri: 'http://www.w3.org/2001/XMLSchema#string'}
classes:
 Thing:
  attributes:
   label: {range: string, required: true}
""",
    )
    return (
        SourceBundle("m", (source,)),
        composed_dependencies(ResolvedDependencies()),
        PreparationProfile(version="semantic-2"),
    )


@lru_cache(maxsize=1)
def prepared():
    return prepare_release(*report_inputs())
